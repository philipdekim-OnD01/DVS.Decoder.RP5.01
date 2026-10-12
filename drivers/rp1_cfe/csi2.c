// SPDX-License-Identifier: GPL-2.0-only
/*
 * RP1 CSI-2 Driver
 *
 * Copyright (C) 2021 - Raspberry Pi Ltd.
 *
 */

#include <linux/delay.h>
#include <linux/ktime.h>
#include <linux/moduleparam.h>
#include <linux/pm_runtime.h>
#include <linux/seq_file.h>
#include <linux/slab.h>

#include <media/videobuf2-dma-contig.h>

#include "csi2.h"
#include "cfe.h"

static bool csi2_track_errors;
module_param_named(track_csi2_errors, csi2_track_errors, bool, 0);
MODULE_PARM_DESC(track_csi2_errors, "track csi-2 errors");

static bool csi2_trace_le;
module_param_named(trace_le, csi2_trace_le, bool, 0);
MODULE_PARM_DESC(trace_le, "diagnostic-only line-end IRQ counting");

/*
 * Diagnostic-only controls for the S5KRC1S PACK_BYTES A/B test.  They are
 * deliberately limited to CSI-2 channel 0 and default to production behavior.
 */
static bool csi2_diag_stride_zero;
module_param_named(diag_stride_zero, csi2_diag_stride_zero, bool, 0644);
MODULE_PARM_DESC(diag_stride_zero,
		 "diagnostic-only: program channel 0 DMA stride as zero");

static int csi2_diag_pack_bytes = -1;
module_param_named(diag_pack_bytes, csi2_diag_pack_bytes, int, 0644);
MODULE_PARM_DESC(diag_pack_bytes,
		 "diagnostic-only channel 0 PACK_BYTES override (-1=normal, 0=off, 1=on)");

#define csi2_dbg_verbose(fmt, arg...)                             \
	do {                                                      \
		if (cfe_debug_verbose)                            \
			dev_dbg(csi2->v4l2_dev->dev, fmt, ##arg); \
	} while (0)
#define csi2_dbg(fmt, arg...) dev_dbg(csi2->v4l2_dev->dev, fmt, ##arg)
#define csi2_info(fmt, arg...) dev_info(csi2->v4l2_dev->dev, fmt, ##arg)
#define csi2_err(fmt, arg...) dev_err(csi2->v4l2_dev->dev, fmt, ##arg)

/* CSI2-DMA registers */
#define CSI2_STATUS		0x000
#define CSI2_QOS		0x004
#define CSI2_DISCARDS_OVERFLOW	0x008
#define CSI2_DISCARDS_INACTIVE	0x00c
#define CSI2_DISCARDS_UNMATCHED	0x010
#define CSI2_DISCARDS_LEN_LIMIT	0x014

#define CSI2_DISCARDS_AMOUNT_SHIFT	0
#define CSI2_DISCARDS_AMOUNT_MASK	GENMASK(23, 0)
#define CSI2_DISCARDS_DT_SHIFT		24
#define CSI2_DISCARDS_DT_MASK		GENMASK(29, 24)
#define CSI2_DISCARDS_VC_SHIFT		30
#define CSI2_DISCARDS_VC_MASK		GENMASK(31, 30)

#define CSI2_LLEV_PANICS	0x018
#define CSI2_ULEV_PANICS	0x01c
#define CSI2_IRQ_MASK		0x020
#define CSI2_IRQ_MASK_IRQ_OVERFLOW		BIT(0)
#define CSI2_IRQ_MASK_IRQ_DISCARD_OVERFLOW	BIT(1)
#define CSI2_IRQ_MASK_IRQ_DISCARD_LENGTH_LIMIT	BIT(2)
#define CSI2_IRQ_MASK_IRQ_DISCARD_UNMATCHED	BIT(3)
#define CSI2_IRQ_MASK_IRQ_DISCARD_INACTIVE	BIT(4)
#define CSI2_IRQ_MASK_IRQ_ALL                                              \
	(CSI2_IRQ_MASK_IRQ_OVERFLOW | CSI2_IRQ_MASK_IRQ_DISCARD_OVERFLOW | \
	 CSI2_IRQ_MASK_IRQ_DISCARD_LENGTH_LIMIT |                          \
	 CSI2_IRQ_MASK_IRQ_DISCARD_UNMATCHED |                             \
	 CSI2_IRQ_MASK_IRQ_DISCARD_INACTIVE)

#define CSI2_CTRL		0x024
#define CSI2_CH_CTRL(x)		((x) * 0x40 + 0x28)
#define CSI2_CH_ADDR0(x)	((x) * 0x40 + 0x2c)
#define CSI2_CH_ADDR1(x)	((x) * 0x40 + 0x3c)
#define CSI2_CH_STRIDE(x)	((x) * 0x40 + 0x30)
#define CSI2_CH_LENGTH(x)	((x) * 0x40 + 0x34)
#define CSI2_CH_DEBUG(x)	((x) * 0x40 + 0x38)
#define CSI2_CH_FRAME_SIZE(x)	((x) * 0x40 + 0x40)
#define CSI2_CH_COMP_CTRL(x)	((x) * 0x40 + 0x44)
#define CSI2_CH_FE_FRAME_ID(x)	((x) * 0x40 + 0x48)

/* CSI2_STATUS */
#define IRQ_FS(x)		(BIT(0) << (x))
#define IRQ_FE(x)		(BIT(4) << (x))
#define IRQ_FE_ACK(x)		(BIT(8) << (x))
#define IRQ_LE(x)		(BIT(12) << (x))
#define IRQ_LE_ACK(x)		(BIT(16) << (x))
#define IRQ_CH_MASK(x)		(IRQ_FS(x) | IRQ_FE(x) | IRQ_FE_ACK(x) | IRQ_LE(x) | IRQ_LE_ACK(x))
#define IRQ_OVERFLOW		BIT(20)
#define IRQ_DISCARD_OVERFLOW	BIT(21)
#define IRQ_DISCARD_LEN_LIMIT	BIT(22)
#define IRQ_DISCARD_UNMATCHED	BIT(23)
#define IRQ_DISCARD_INACTIVE	BIT(24)

/* CSI2_CTRL */
#define EOP_IS_EOL		BIT(0)

/* CSI2_CH_CTRL */
#define DMA_EN			BIT(0)
#define FORCE			BIT(3)
#define AUTO_ARM		BIT(4)
#define IRQ_EN_FS		BIT(13)
#define IRQ_EN_FE		BIT(14)
#define IRQ_EN_FE_ACK		BIT(15)
#define IRQ_EN_LE		BIT(16)
#define IRQ_EN_LE_ACK		BIT(17)
#define FLUSH_FE		BIT(28)
#define PACK_LINE		BIT(29)
#define PACK_BYTES		BIT(30)
#define CH_MODE_MASK		GENMASK(2, 1)
#define VC_MASK			GENMASK(6, 5)
#define DT_MASK			GENMASK(12, 7)
#define LC_MASK			GENMASK(27, 18)

/* CHx_COMPRESSION_CONTROL */
#define COMP_OFFSET_MASK	GENMASK(15, 0)
#define COMP_SHIFT_MASK		GENMASK(19, 16)
#define COMP_MODE_MASK		GENMASK(25, 24)

static inline u32 csi2_reg_read(struct csi2_device *csi2, u32 offset)
{
	return readl(csi2->base + offset);
}

static inline void csi2_reg_write(struct csi2_device *csi2, u32 offset, u32 val)
{
	writel(val, csi2->base + offset);
	csi2_dbg_verbose("csi2: write 0x%04x -> 0x%03x\n", val, offset);
}

static inline void set_field(u32 *valp, u32 field, u32 mask)
{
	u32 val = *valp;

	val &= ~mask;
	val |= (field << __ffs(mask)) & mask;
	*valp = val;
}

static int csi2_regs_show(struct seq_file *s, void *data)
{
	struct csi2_device *csi2 = s->private;
	unsigned int i;
	int ret;

	ret = pm_runtime_resume_and_get(csi2->v4l2_dev->dev);
	if (ret)
		return ret;

#define DUMP(reg) seq_printf(s, #reg " \t0x%08x\n", csi2_reg_read(csi2, reg))
#define DUMP_CH(idx, reg) seq_printf(s, #reg "(%u) \t0x%08x\n", idx, csi2_reg_read(csi2, reg(idx)))

	DUMP(CSI2_STATUS);
	DUMP(CSI2_DISCARDS_OVERFLOW);
	DUMP(CSI2_DISCARDS_INACTIVE);
	DUMP(CSI2_DISCARDS_UNMATCHED);
	DUMP(CSI2_DISCARDS_LEN_LIMIT);
	DUMP(CSI2_LLEV_PANICS);
	DUMP(CSI2_ULEV_PANICS);
	DUMP(CSI2_IRQ_MASK);
	DUMP(CSI2_CTRL);

	for (i = 0; i < CSI2_NUM_CHANNELS; ++i) {
		DUMP_CH(i, CSI2_CH_CTRL);
		DUMP_CH(i, CSI2_CH_ADDR0);
		DUMP_CH(i, CSI2_CH_ADDR1);
		DUMP_CH(i, CSI2_CH_STRIDE);
		DUMP_CH(i, CSI2_CH_LENGTH);
		DUMP_CH(i, CSI2_CH_DEBUG);
		DUMP_CH(i, CSI2_CH_FRAME_SIZE);
		DUMP_CH(i, CSI2_CH_COMP_CTRL);
		DUMP_CH(i, CSI2_CH_FE_FRAME_ID);
	}

#undef DUMP
#undef DUMP_CH

	pm_runtime_put(csi2->v4l2_dev->dev);

	return 0;
}

DEFINE_SHOW_ATTRIBUTE(csi2_regs);

static int csi2_errors_show(struct seq_file *s, void *data)
{
	struct csi2_device *csi2 = s->private;
	unsigned long flags;
	u32 discards_table[DISCARDS_TABLE_NUM_VCS][DISCARDS_TABLE_NUM_ENTRIES];
	u32 discards_dt_table[DISCARDS_TABLE_NUM_ENTRIES];
	u32 overflows;

	spin_lock_irqsave(&csi2->errors_lock, flags);

	memcpy(discards_table, csi2->discards_table, sizeof(discards_table));
	memcpy(discards_dt_table, csi2->discards_dt_table,
	       sizeof(discards_dt_table));
	overflows = csi2->overflows;

	csi2->overflows = 0;
	memset(csi2->discards_table, 0, sizeof(discards_table));
	memset(csi2->discards_dt_table, 0, sizeof(discards_dt_table));

	spin_unlock_irqrestore(&csi2->errors_lock, flags);

	seq_printf(s, "Overflows %u\n", overflows);
	seq_puts(s, "Discards:\n");
	seq_puts(s, "VC            OVLF        LEN  UNMATCHED   INACTIVE\n");

	for (unsigned int vc = 0; vc < DISCARDS_TABLE_NUM_VCS; ++vc) {
		seq_printf(s, "%u       %10u %10u %10u %10u\n", vc,
			   discards_table[vc][DISCARDS_TABLE_OVERFLOW],
			   discards_table[vc][DISCARDS_TABLE_LENGTH_LIMIT],
			   discards_table[vc][DISCARDS_TABLE_UNMATCHED],
			   discards_table[vc][DISCARDS_TABLE_INACTIVE]);
	}

	seq_printf(s, "Last DT %10u %10u %10u %10u\n",
		   discards_dt_table[DISCARDS_TABLE_OVERFLOW],
		   discards_dt_table[DISCARDS_TABLE_LENGTH_LIMIT],
		   discards_dt_table[DISCARDS_TABLE_UNMATCHED],
		   discards_dt_table[DISCARDS_TABLE_INACTIVE]);

	return 0;
}

DEFINE_SHOW_ATTRIBUTE(csi2_errors);

static int csi2_packet_counts_show(struct seq_file *s, void *data)
{
	struct csi2_device *csi2 = s->private;
	struct csi2_packet_diag *snapshot;
	unsigned long flags;
	unsigned int channel;

	snapshot = kmalloc(sizeof(csi2->packet_diag), GFP_KERNEL);
	if (!snapshot)
		return -ENOMEM;

	spin_lock_irqsave(&csi2->errors_lock, flags);
	memcpy(snapshot, csi2->packet_diag, sizeof(csi2->packet_diag));
	spin_unlock_irqrestore(&csi2->errors_lock, flags);

	for (channel = 0; channel < CSI2_NUM_CHANNELS; channel++) {
		struct csi2_packet_diag *diag = &snapshot[channel];
		u32 hist_126 = 0, hist_127 = 0, hist_128 = 0, hist_159 = 0;
		u32 hist_other = 0;
		u32 start = (diag->sample_head + CSI2_PACKET_DIAG_SAMPLES -
			     diag->sample_count) % CSI2_PACKET_DIAG_SAMPLES;
		u32 n;

		for (n = 0; n < diag->sample_count; n++) {
			const struct csi2_packet_diag_sample *sample =
				&diag->samples[(start + n) % CSI2_PACKET_DIAG_SAMPLES];

			switch (sample->accepted_packets) {
			case 126:
				hist_126++;
				break;
			case 127:
				hist_127++;
				break;
			case 128:
				hist_128++;
				break;
			case 159:
				hist_159++;
				break;
			default:
				hist_other++;
				break;
			}
		}

		seq_printf(s,
			   "channel=%u vc=%u dt=0x%02x configured_height=%u fs=%llu fe=%llu le_total=%llu debug_delta_total=%llu incomplete=%llu samples=%u active=%u current=%u\n",
			   channel, diag->vc, diag->dt, diag->configured_height,
			   (unsigned long long)diag->fs_total,
			   (unsigned long long)diag->fe_total,
			   (unsigned long long)diag->le_total,
			   (unsigned long long)diag->debug_delta_total,
			   (unsigned long long)diag->incomplete_frames,
			   diag->sample_count, diag->frame_active,
			   diag->current_packets);
		seq_printf(s,
			   "histogram channel=%u 126=%u 127=%u 128=%u 159=%u other=%u\n",
			   channel, hist_126, hist_127, hist_128, hist_159,
			   hist_other);

		for (n = 0; n < diag->sample_count; n++) {
			const struct csi2_packet_diag_sample *sample =
				&diag->samples[(start + n) % CSI2_PACKET_DIAG_SAMPLES];

			seq_printf(s,
				   "sample channel=%u index=%u fs=%u accepted_dt2a_packets=%u ch_debug_frame=%u ch_debug_line=%u irq_status=0x%08x\n",
				   channel, n, sample->fs_sequence,
				   sample->accepted_packets,
				   sample->fe_ch_debug >> 16,
				   sample->fe_ch_debug & 0xffff,
				   sample->fe_irq_status);
		}
	}

	kfree(snapshot);
	return 0;
}

DEFINE_SHOW_ATTRIBUTE(csi2_packet_counts);

static const char *csi2_error_diag_name(u32 type)
{
	static const char * const names[] = {
		"DISCARD_OVERFLOW",
		"LEN_LIMIT",
		"UNMATCHED",
		"INACTIVE",
		"OVERFLOW",
	};

	return type < ARRAY_SIZE(names) ? names[type] : "UNKNOWN";
}

static int csi2_irq_trace_show(struct seq_file *s, void *data)
{
	struct csi2_device *csi2 = s->private;
	struct csi2_packet_diag *packet_snapshot;
	struct csi2_error_diag_sample *error_snapshot;
	unsigned long flags;
	u32 error_head, error_count, error_start;
	unsigned int channel;

	packet_snapshot = kmalloc(sizeof(csi2->packet_diag), GFP_KERNEL);
	error_snapshot = kmalloc_array(CSI2_ERROR_DIAG_SAMPLES,
				       sizeof(*error_snapshot), GFP_KERNEL);
	if (!packet_snapshot || !error_snapshot) {
		kfree(packet_snapshot);
		kfree(error_snapshot);
		return -ENOMEM;
	}

	spin_lock_irqsave(&csi2->errors_lock, flags);
	memcpy(packet_snapshot, csi2->packet_diag, sizeof(csi2->packet_diag));
	memcpy(error_snapshot, csi2->error_diag, sizeof(csi2->error_diag));
	error_head = csi2->error_diag_head;
	error_count = csi2->error_diag_count;
	spin_unlock_irqrestore(&csi2->errors_lock, flags);

	seq_printf(s, "trace_le=%u error_samples=%u\n",
		   csi2_trace_le, error_count);
	for (channel = 0; channel < CSI2_NUM_CHANNELS; channel++) {
		struct csi2_packet_diag *diag = &packet_snapshot[channel];
		u32 start = (diag->sample_head + CSI2_PACKET_DIAG_SAMPLES -
			     diag->sample_count) % CSI2_PACKET_DIAG_SAMPLES;
		u32 n;

		seq_printf(s,
			   "channel=%u vc=%u dt=0x%02x height=%u fs_total=%llu fe_total=%llu samples=%u incomplete=%llu\n",
			   channel, diag->vc, diag->dt, diag->configured_height,
			   (unsigned long long)diag->fs_total,
			   (unsigned long long)diag->fe_total,
			   diag->sample_count,
			   (unsigned long long)diag->incomplete_frames);
		for (n = 0; n < diag->sample_count; n++) {
			const struct csi2_packet_diag_sample *sample =
				&diag->samples[(start + n) %
					       CSI2_PACKET_DIAG_SAMPLES];
			u64 duration = sample->fe_time_ns >= sample->fs_time_ns ?
				sample->fe_time_ns - sample->fs_time_ns : 0;

			seq_printf(s,
				   "frame ch=%u index=%u fs_seq=%u fs_ns=%llu fe_ns=%llu duration_ns=%llu fs_status=0x%08x fe_status=0x%08x fs_debug=0x%08x fe_debug=0x%08x fs_line_raw=%u fe_line_raw=%u line_delta=%u fs_fe_id=0x%08x fe_fe_id=0x%08x le_count=%u len_events=%u len_amount=%u len_dt=0x%02x len_vc=%u unmatched_events=%u unmatched_amount=%u unmatched_dt=0x%02x unmatched_vc=%u v4l2_sequence=NA\n",
				   channel, n, sample->fs_sequence,
				   (unsigned long long)sample->fs_time_ns,
				   (unsigned long long)sample->fe_time_ns,
				   (unsigned long long)duration,
				   sample->fs_irq_status,
				   sample->fe_irq_status,
				   sample->fs_ch_debug,
				   sample->fe_ch_debug,
				   sample->fs_ch_debug & 0xffff,
				   sample->fe_ch_debug & 0xffff,
				   sample->accepted_packets,
				   sample->fs_fe_frame_id,
				   sample->fe_fe_frame_id,
				   sample->le_count,
				   sample->len_events,
				   sample->len_amount,
				   sample->len_dt,
				   sample->len_vc,
				   sample->unmatched_events,
				   sample->unmatched_amount,
				   sample->unmatched_dt,
				   sample->unmatched_vc);
		}
	}

	error_start = (error_head + CSI2_ERROR_DIAG_SAMPLES - error_count) %
		      CSI2_ERROR_DIAG_SAMPLES;
	for (u32 n = 0; n < error_count; n++) {
		const struct csi2_error_diag_sample *sample =
			&error_snapshot[(error_start + n) %
					CSI2_ERROR_DIAG_SAMPLES];

		seq_printf(s,
			   "error index=%u ns=%llu since_fs_ns=%llu type=%s amount=%u dt=0x%02x vc=%u channel=%u height=%u fs_seq=%u frame_active=%u status=0x%08x ch_debug=0x%08x raw_line=%u fe_frame_id=0x%08x v4l2_sequence=NA\n",
			   n, (unsigned long long)sample->ktime_ns,
			   (unsigned long long)sample->ns_since_fs,
			   csi2_error_diag_name(sample->error_type),
			   sample->amount, sample->dt, sample->vc,
			   sample->channel, sample->configured_height,
			   sample->fs_sequence, sample->frame_active,
			   sample->csi2_status, sample->ch_debug,
			   sample->ch_debug & 0xffff,
			   sample->fe_frame_id);
	}

	kfree(packet_snapshot);
	kfree(error_snapshot);
	return 0;
}

DEFINE_SHOW_ATTRIBUTE(csi2_irq_trace);

static void csi2_packet_diag_reset(struct csi2_device *csi2,
				   unsigned int channel, u8 vc, u8 dt,
				   unsigned int height)
{
	unsigned long flags;
	struct csi2_packet_diag *diag;

	spin_lock_irqsave(&csi2->errors_lock, flags);
	diag = &csi2->packet_diag[channel];
	memset(diag, 0, sizeof(*diag));
	diag->vc = vc;
	diag->dt = dt;
	diag->configured_height = height;
	if (channel == 0) {
		csi2->error_diag_head = 0;
		csi2->error_diag_count = 0;
	}
	spin_unlock_irqrestore(&csi2->errors_lock, flags);
}

static void csi2_packet_diag_irq(struct csi2_device *csi2,
				 unsigned int channel, u32 status, u32 dbg,
				 u32 fe_frame_id)
{
	struct csi2_packet_diag *diag = &csi2->packet_diag[channel];
	u64 now = ktime_get_ns();

	spin_lock(&csi2->errors_lock);

	if (status & IRQ_FS(channel)) {
		if (diag->frame_active)
			diag->incomplete_frames++;
		diag->current_packets = 0;
		diag->frame_active = true;
		diag->fs_total++;
		diag->current_fs_time_ns = now;
		diag->current_fs_ch_debug = dbg;
		diag->current_fs_fe_frame_id = fe_frame_id;
		diag->current_fs_irq_status = status;
		diag->current_len_events = 0;
		diag->current_len_amount = 0;
		diag->current_unmatched_events = 0;
		diag->current_unmatched_amount = 0;
		diag->current_len_dt = 0;
		diag->current_len_vc = 0;
		diag->current_unmatched_dt = 0;
		diag->current_unmatched_vc = 0;
	}

	if ((status & IRQ_LE(channel)) && diag->frame_active) {
		diag->current_packets++;
		diag->le_total++;
	}

	if ((status & IRQ_FE_ACK(channel)) && diag->frame_active) {
		struct csi2_packet_diag_sample *sample =
			&diag->samples[diag->sample_head];
		u16 line = dbg & 0xffff;
		u16 delta = diag->have_previous_fe ?
			(u16)(line - diag->previous_fe_line) : line;

		sample->fs_time_ns = diag->current_fs_time_ns;
		sample->fe_time_ns = now;
		sample->fs_sequence = (u32)diag->fs_total;
		sample->accepted_packets = delta;
		sample->fs_ch_debug = diag->current_fs_ch_debug;
		sample->fe_ch_debug = dbg;
		sample->fs_fe_frame_id = diag->current_fs_fe_frame_id;
		sample->fe_fe_frame_id = fe_frame_id;
		sample->fs_irq_status = diag->current_fs_irq_status;
		sample->fe_irq_status = status;
		sample->le_count = diag->current_packets;
		sample->len_events = diag->current_len_events;
		sample->len_amount = diag->current_len_amount;
		sample->unmatched_events = diag->current_unmatched_events;
		sample->unmatched_amount = diag->current_unmatched_amount;
		sample->len_dt = diag->current_len_dt;
		sample->len_vc = diag->current_len_vc;
		sample->unmatched_dt = diag->current_unmatched_dt;
		sample->unmatched_vc = diag->current_unmatched_vc;
		diag->debug_delta_total += delta;
		diag->previous_fe_line = line;
		diag->have_previous_fe = true;
		diag->sample_head =
			(diag->sample_head + 1) % CSI2_PACKET_DIAG_SAMPLES;
		if (diag->sample_count < CSI2_PACKET_DIAG_SAMPLES)
			diag->sample_count++;
		diag->fe_total++;
		diag->frame_active = false;
	}

	spin_unlock(&csi2->errors_lock);
}

static void csi2_error_diag_record_locked(struct csi2_device *csi2,
					  u32 status, unsigned int error_type,
					  u32 amount, u8 dt, u8 vc)
{
	struct csi2_error_diag_sample *sample;
	struct csi2_packet_diag *diag = NULL;
	unsigned int channel, diag_channel = 0xff;
	u64 now = ktime_get_ns();

	for (channel = 0; channel < CSI2_NUM_CHANNELS; channel++) {
		struct csi2_packet_diag *candidate = &csi2->packet_diag[channel];

		if (candidate->vc != vc || candidate->dt != dt)
			continue;
		if (!diag) {
			diag = candidate;
			diag_channel = channel;
		}
		if (candidate->frame_active) {
			diag = candidate;
			diag_channel = channel;
			break;
		}
	}

	sample = &csi2->error_diag[csi2->error_diag_head];
	memset(sample, 0, sizeof(*sample));
	sample->ktime_ns = now;
	sample->csi2_status = status;
	sample->error_type = error_type;
	sample->amount = amount;
	sample->dt = dt;
	sample->vc = vc;
	sample->channel = diag_channel;
	sample->v4l2_sequence = ~0U;

	if (diag) {
		sample->frame_active = diag->frame_active;
		sample->configured_height = diag->configured_height;
		sample->fs_sequence = (u32)diag->fs_total;
		sample->ch_debug =
			csi2_reg_read(csi2, CSI2_CH_DEBUG(diag_channel));
		sample->fe_frame_id =
			csi2_reg_read(csi2, CSI2_CH_FE_FRAME_ID(diag_channel));
		if (diag->frame_active && diag->current_fs_time_ns)
			sample->ns_since_fs = now - diag->current_fs_time_ns;

		if (diag->frame_active &&
		    error_type == DISCARDS_TABLE_LENGTH_LIMIT) {
			diag->current_len_events++;
			diag->current_len_amount += amount;
			diag->current_len_dt = dt;
			diag->current_len_vc = vc;
		} else if (diag->frame_active &&
			   error_type == DISCARDS_TABLE_UNMATCHED) {
			diag->current_unmatched_events++;
			diag->current_unmatched_amount += amount;
			diag->current_unmatched_dt = dt;
			diag->current_unmatched_vc = vc;
		}
	}

	csi2->error_diag_head =
		(csi2->error_diag_head + 1) % CSI2_ERROR_DIAG_SAMPLES;
	if (csi2->error_diag_count < CSI2_ERROR_DIAG_SAMPLES)
		csi2->error_diag_count++;
}

static void csi2_isr_handle_errors(struct csi2_device *csi2, u32 status)
{
	spin_lock(&csi2->errors_lock);

	if (status & IRQ_OVERFLOW) {
		csi2->overflows++;
		csi2_error_diag_record_locked(csi2, status,
					      DISCARDS_TABLE_NUM_ENTRIES,
					      1, 0xff, 0xff);
	}

	for (unsigned int i = 0; i < DISCARDS_TABLE_NUM_ENTRIES; ++i) {
		static const u32 discard_bits[] = {
			IRQ_DISCARD_OVERFLOW,
			IRQ_DISCARD_LEN_LIMIT,
			IRQ_DISCARD_UNMATCHED,
			IRQ_DISCARD_INACTIVE,
		};
		static const u8 discard_regs[] = {
			CSI2_DISCARDS_OVERFLOW,
			CSI2_DISCARDS_LEN_LIMIT,
			CSI2_DISCARDS_UNMATCHED,
			CSI2_DISCARDS_INACTIVE,
		};
		u32 amount;
		u8 dt, vc;
		u32 v;

		if (!(status & discard_bits[i]))
			continue;

		v = csi2_reg_read(csi2, discard_regs[i]);
		csi2_reg_write(csi2, discard_regs[i], 0);

		amount = (v & CSI2_DISCARDS_AMOUNT_MASK) >>
			 CSI2_DISCARDS_AMOUNT_SHIFT;
		dt = (v & CSI2_DISCARDS_DT_MASK) >> CSI2_DISCARDS_DT_SHIFT;
		vc = (v & CSI2_DISCARDS_VC_MASK) >> CSI2_DISCARDS_VC_SHIFT;

		csi2->discards_table[vc][i] += amount;
		csi2->discards_dt_table[i] = dt;
		csi2_error_diag_record_locked(csi2, status, i, amount, dt, vc);
	}

	spin_unlock(&csi2->errors_lock);
}

void csi2_isr(struct csi2_device *csi2, bool *sof, bool *eof)
{
	unsigned int i;
	u32 status;
	u32 dbg[CSI2_NUM_CHANNELS] = { 0 };
	u32 fe_frame_id[CSI2_NUM_CHANNELS] = { 0 };
	bool channel_irq[CSI2_NUM_CHANNELS] = { false };

	status = csi2_reg_read(csi2, CSI2_STATUS);
	csi2_dbg_verbose("ISR: STA: 0x%x\n", status);

	/* Write value back to clear the interrupts */
	csi2_reg_write(csi2, CSI2_STATUS, status);

	/*
	 * Establish a new FS sample before attributing error IRQs, then snapshot
	 * errors, and only afterwards close FE_ACK. This preserves errors that
	 * share an IRQ status word with either frame boundary.
	 */
	for (i = 0; i < CSI2_NUM_CHANNELS; i++) {
		if ((status & IRQ_CH_MASK(i)) == 0)
			continue;

		channel_irq[i] = true;
		dbg[i] = csi2_reg_read(csi2, CSI2_CH_DEBUG(i));
		fe_frame_id[i] =
			csi2_reg_read(csi2, CSI2_CH_FE_FRAME_ID(i));
		if (status & IRQ_FS(i))
			csi2_packet_diag_irq(csi2, i, IRQ_FS(i), dbg[i],
					     fe_frame_id[i]);
	}

	if (csi2_track_errors)
		csi2_isr_handle_errors(csi2, status);

	for (i = 0; i < CSI2_NUM_CHANNELS; i++) {
		if (!channel_irq[i])
			continue;

		csi2_packet_diag_irq(csi2, i, status & ~IRQ_FS(i), dbg[i],
				     fe_frame_id[i]);

		csi2_dbg_verbose("ISR: [%u], %s%s%s%s%s frame: %u line: %u\n",
				 i, (status & IRQ_FS(i)) ? "FS " : "",
				 (status & IRQ_FE(i)) ? "FE " : "",
				 (status & IRQ_FE_ACK(i)) ? "FE_ACK " : "",
				 (status & IRQ_LE(i)) ? "LE " : "",
				 (status & IRQ_LE_ACK(i)) ? "LE_ACK " : "",
				 dbg[i] >> 16,
				 csi2->num_lines[i] ?
					 ((dbg[i] & 0xffff) % csi2->num_lines[i]) :
					 0);

		sof[i] = !!(status & IRQ_FS(i));
		eof[i] = !!(status & IRQ_FE_ACK(i));
	}

}

void csi2_set_buffer(struct csi2_device *csi2, unsigned int channel,
		     dma_addr_t dmaaddr, unsigned int stride, unsigned int size)
{
	u64 addr = dmaaddr;

	if (channel == 0 && csi2_diag_stride_zero)
		stride = 0;
	/*
	 * ADDRESS0 must be written last as it triggers the double buffering
	 * mechanism for all buffer registers within the hardware.
	 */
	addr >>= 4;
	csi2_reg_write(csi2, CSI2_CH_LENGTH(channel), size >> 4);
	csi2_reg_write(csi2, CSI2_CH_STRIDE(channel), stride >> 4);
	csi2_reg_write(csi2, CSI2_CH_ADDR1(channel), addr >> 32);
	csi2_reg_write(csi2, CSI2_CH_ADDR0(channel), addr & 0xffffffff);
}

void csi2_set_compression(struct csi2_device *csi2, unsigned int channel,
			  enum csi2_compression_mode mode, unsigned int shift,
			  unsigned int offset)
{
	u32 compression = 0;

	set_field(&compression, COMP_OFFSET_MASK, offset);
	set_field(&compression, COMP_SHIFT_MASK, shift);
	set_field(&compression, COMP_MODE_MASK, mode);
	csi2_reg_write(csi2, CSI2_CH_COMP_CTRL(channel), compression);
}

static int csi2_get_vc_dt_fallback(struct csi2_device *csi2,
				   unsigned int channel, u8 *vc, u8 *dt)
{
	struct v4l2_subdev *sd = &csi2->sd;
	struct v4l2_subdev_state *state;
	struct v4l2_mbus_framefmt *fmt;
	const struct cfe_fmt *cfe_fmt;

	state = v4l2_subdev_get_locked_active_state(sd);

	/* Without Streams API, the channel number matches the sink pad */
	fmt = v4l2_subdev_state_get_format(state, channel);
	if (!fmt)
		return -EINVAL;

	cfe_fmt = find_format_by_code(fmt->code);
	if (!cfe_fmt)
		return -EINVAL;

	*vc = 0;
	*dt = cfe_fmt->csi_dt;

	return 0;
}

static int csi2_get_vc_dt(struct csi2_device *csi2, unsigned int channel,
			  u8 *vc, u8 *dt)
{
	struct v4l2_mbus_frame_desc remote_desc;
	const struct media_pad *remote_pad;
	struct v4l2_subdev *source_sd;
	int ret;

	/* Without Streams API, the channel number matches the sink pad */
	remote_pad = media_pad_remote_pad_first(&csi2->pad[channel]);
	if (!remote_pad)
		return -EPIPE;

	source_sd = media_entity_to_v4l2_subdev(remote_pad->entity);

	ret = v4l2_subdev_call(source_sd, pad, get_frame_desc,
			       remote_pad->index, &remote_desc);
	if (ret == -ENOIOCTLCMD) {
		csi2_dbg("source does not support get_frame_desc, use fallback\n");
		return csi2_get_vc_dt_fallback(csi2, channel, vc, dt);
	} else if (ret) {
		csi2_err("Failed to get frame descriptor\n");
		return ret;
	}

	if (remote_desc.type != V4L2_MBUS_FRAME_DESC_TYPE_CSI2) {
		csi2_err("Frame descriptor does not describe CSI-2 link");
		return -EINVAL;
	}

	if (remote_desc.num_entries != 1) {
		csi2_err("Frame descriptor does not have a single entry");
		return -EINVAL;
	}

	*vc = remote_desc.entry[0].bus.csi2.vc;
	*dt = remote_desc.entry[0].bus.csi2.dt;

	return 0;
}

void csi2_start_channel(struct csi2_device *csi2, unsigned int channel,
			enum csi2_mode mode, bool auto_arm,
			bool pack_bytes, unsigned int width,
			unsigned int height)
{
	u32 ctrl;
	int ret;
	u8 vc, dt;

	ret = csi2_get_vc_dt(csi2, channel, &vc, &dt);
	if (ret)
		return;

	csi2_packet_diag_reset(csi2, channel, vc, dt, height);

	csi2_dbg("%s [%u]\n", __func__, channel);

	csi2_reg_write(csi2, CSI2_CH_CTRL(channel), 0);
	csi2_reg_write(csi2, CSI2_CH_DEBUG(channel), 0);
	csi2_reg_write(csi2, CSI2_STATUS, IRQ_CH_MASK(channel));

	if (channel == 0 && csi2_diag_pack_bytes >= 0) {
		WARN_ON_ONCE(csi2_diag_pack_bytes > 1);
		pack_bytes = !!csi2_diag_pack_bytes;
	}

	/* Enable channel and FS/FE interrupts. */
	ctrl = DMA_EN | IRQ_EN_FS | IRQ_EN_FE_ACK | PACK_LINE;
	if (csi2_trace_le)
		ctrl |= IRQ_EN_LE;
	/* PACK_BYTES ensures no striding for embedded data. */
	if (pack_bytes)
		ctrl |= PACK_BYTES;

	if (auto_arm)
		ctrl |= AUTO_ARM;

	if (width && height) {
		set_field(&ctrl, mode, CH_MODE_MASK);
		csi2_reg_write(csi2, CSI2_CH_FRAME_SIZE(channel),
			       (height << 16) | width);
	} else {
		set_field(&ctrl, 0x0, CH_MODE_MASK);
		csi2_reg_write(csi2, CSI2_CH_FRAME_SIZE(channel), 0);
	}

	set_field(&ctrl, vc, VC_MASK);
	set_field(&ctrl, dt, DT_MASK);
	csi2_reg_write(csi2, CSI2_CH_CTRL(channel), ctrl);
	csi2->num_lines[channel] = height;
}

void csi2_stop_channel(struct csi2_device *csi2, unsigned int channel)
{
	csi2_dbg("%s [%u]\n", __func__, channel);

	/* Channel disable.  Use FORCE to allow stopping mid-frame. */
	csi2_reg_write(csi2, CSI2_CH_CTRL(channel), FORCE);
	/* Latch the above change by writing to the ADDR0 register. */
	csi2_reg_write(csi2, CSI2_CH_ADDR0(channel), 0);
	/* Write this again, the HW needs it! */
	csi2_reg_write(csi2, CSI2_CH_ADDR0(channel), 0);
}

void csi2_open_rx(struct csi2_device *csi2)
{
	csi2_reg_write(csi2, CSI2_IRQ_MASK,
		       csi2_track_errors ? CSI2_IRQ_MASK_IRQ_ALL : 0);

	dphy_start(&csi2->dphy);

	csi2_reg_write(csi2, CSI2_CTRL,
		       csi2->multipacket_line ? 0 : EOP_IS_EOL);
}

void csi2_close_rx(struct csi2_device *csi2)
{
	dphy_stop(&csi2->dphy);

	csi2_reg_write(csi2, CSI2_IRQ_MASK, 0);
}

static int csi2_init_cfg(struct v4l2_subdev *sd,
			 struct v4l2_subdev_state *state)
{
	struct v4l2_mbus_framefmt *fmt;

	for (unsigned int i = 0; i < CSI2_NUM_CHANNELS; ++i) {
		const struct v4l2_mbus_framefmt *def_fmt;

		/* CSI2_CH1_EMBEDDED */
		if (i == 1)
			def_fmt = &cfe_default_meta_format;
		else
			def_fmt = &cfe_default_format;

		fmt = v4l2_subdev_state_get_format(state, i);
		*fmt = *def_fmt;

		fmt = v4l2_subdev_state_get_format(state, i + CSI2_NUM_CHANNELS);
		*fmt = *def_fmt;
	}

	return 0;
}

static int csi2_pad_set_fmt(struct v4l2_subdev *sd,
			    struct v4l2_subdev_state *state,
			    struct v4l2_subdev_format *format)
{
	if (format->pad < CSI2_NUM_CHANNELS) {
		/*
		 * Store the sink pad format and propagate it to the source pad.
		 */

		struct v4l2_mbus_framefmt *fmt;

		fmt = v4l2_subdev_state_get_format(state, format->pad);
		if (!fmt)
			return -EINVAL;

		*fmt = format->format;

		fmt = v4l2_subdev_state_get_format(state,
			format->pad + CSI2_NUM_CHANNELS);
		if (!fmt)
			return -EINVAL;

		format->format.field = V4L2_FIELD_NONE;

		*fmt = format->format;
	} else {
		/*
		 * Only allow changing the source pad mbus code.
		 */

		struct v4l2_mbus_framefmt *sink_fmt, *source_fmt;
		u32 sink_code;
		u32 code;

		sink_fmt = v4l2_subdev_state_get_format(state,
			format->pad - CSI2_NUM_CHANNELS);
		if (!sink_fmt)
			return -EINVAL;

		source_fmt = v4l2_subdev_state_get_format(state, format->pad);
		if (!source_fmt)
			return -EINVAL;

		sink_code = sink_fmt->code;
		code = format->format.code;

		/*
		 * If the source code from the user does not match the code in
		 * the sink pad, check that the source code matches either the
		 * 16-bit version or the compressed version of the sink code.
		 */

		if (code != sink_code &&
		    (code == cfe_find_16bit_code(sink_code) ||
		     code == cfe_find_compressed_code(sink_code)))
			source_fmt->code = code;

		format->format.code = source_fmt->code;
	}

	return 0;
}

static const struct v4l2_subdev_internal_ops csi2_internal_ops = {
	.init_state = csi2_init_cfg,
};

static const struct v4l2_subdev_pad_ops csi2_subdev_pad_ops = {
	.get_fmt = v4l2_subdev_get_fmt,
	.set_fmt = csi2_pad_set_fmt,
	.link_validate = v4l2_subdev_link_validate_default,
};

static const struct media_entity_operations csi2_entity_ops = {
	.link_validate = v4l2_subdev_link_validate,
};

static const struct v4l2_subdev_ops csi2_subdev_ops = {
	.pad = &csi2_subdev_pad_ops,
};

int csi2_init(struct csi2_device *csi2, struct dentry *debugfs)
{
	unsigned int i, ret;

	spin_lock_init(&csi2->errors_lock);

	csi2->dphy.dev = csi2->v4l2_dev->dev;
	dphy_probe(&csi2->dphy);

	debugfs_create_file("csi2_regs", 0444, debugfs, csi2, &csi2_regs_fops);

	if (csi2_track_errors)
		debugfs_create_file("csi2_errors", 0444, debugfs, csi2,
				    &csi2_errors_fops);

	debugfs_create_file("csi2_packet_counts", 0444, debugfs, csi2,
			    &csi2_packet_counts_fops);
	debugfs_create_file("csi2_irq_trace", 0444, debugfs, csi2,
			    &csi2_irq_trace_fops);

	for (i = 0; i < CSI2_NUM_CHANNELS * 2; i++)
		csi2->pad[i].flags = i < CSI2_NUM_CHANNELS ?
				     MEDIA_PAD_FL_SINK : MEDIA_PAD_FL_SOURCE;

	ret = media_entity_pads_init(&csi2->sd.entity, ARRAY_SIZE(csi2->pad),
				     csi2->pad);
	if (ret)
		return ret;

	/* Initialize subdev */
	v4l2_subdev_init(&csi2->sd, &csi2_subdev_ops);
	csi2->sd.internal_ops = &csi2_internal_ops;
	csi2->sd.entity.function = MEDIA_ENT_F_VID_IF_BRIDGE;
	csi2->sd.entity.ops = &csi2_entity_ops;
	csi2->sd.flags = V4L2_SUBDEV_FL_HAS_DEVNODE;
	csi2->sd.owner = THIS_MODULE;
	snprintf(csi2->sd.name, sizeof(csi2->sd.name), "csi2");

	ret = v4l2_subdev_init_finalize(&csi2->sd);
	if (ret)
		goto err_entity_cleanup;

	ret = v4l2_device_register_subdev(csi2->v4l2_dev, &csi2->sd);
	if (ret) {
		csi2_err("Failed register csi2 subdev (%d)\n", ret);
		goto err_subdev_cleanup;
	}

	return 0;

err_subdev_cleanup:
	v4l2_subdev_cleanup(&csi2->sd);
err_entity_cleanup:
	media_entity_cleanup(&csi2->sd.entity);

	return ret;
}

void csi2_uninit(struct csi2_device *csi2)
{
	v4l2_device_unregister_subdev(&csi2->sd);
	v4l2_subdev_cleanup(&csi2->sd);
	media_entity_cleanup(&csi2->sd.entity);
}
