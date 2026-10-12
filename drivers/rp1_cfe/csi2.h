/* SPDX-License-Identifier: GPL-2.0 */
/*
 * RP1 CSI-2 driver.
 * Copyright (c) 2021 Raspberry Pi Ltd.
 *
 */
#ifndef _RP1_CSI2_
#define _RP1_CSI2_

#include <linux/debugfs.h>
#include <linux/io.h>
#include <linux/types.h>
#include <media/v4l2-device.h>
#include <media/v4l2-subdev.h>

#include "dphy.h"

#define CSI2_NUM_CHANNELS 4
#define CSI2_PACKET_DIAG_SAMPLES 256
#define CSI2_ERROR_DIAG_SAMPLES 4096

#define DISCARDS_TABLE_NUM_VCS 4

enum csi2_mode {
	CSI2_MODE_NORMAL = 0,
	CSI2_MODE_REMAP = 1,
	CSI2_MODE_COMPRESSED = 2,
	CSI2_MODE_FE_STREAMING = 3,
};

enum csi2_compression_mode {
	CSI2_COMPRESSION_DELTA = 1,
	CSI2_COMPRESSION_SIMPLE = 2,
	CSI2_COMPRESSION_COMBINED = 3,
};

struct csi2_cfg {
	u16 width;
	u16 height;
	u32 stride;
	u32 buffer_size;
};

enum discards_table_index {
	DISCARDS_TABLE_OVERFLOW = 0,
	DISCARDS_TABLE_LENGTH_LIMIT,
	DISCARDS_TABLE_UNMATCHED,
	DISCARDS_TABLE_INACTIVE,
	DISCARDS_TABLE_NUM_ENTRIES,
};

struct csi2_packet_diag_sample {
	u64 fs_time_ns;
	u64 fe_time_ns;
	u32 fs_sequence;
	u32 accepted_packets;
	u32 fs_ch_debug;
	u32 fe_ch_debug;
	u32 fs_fe_frame_id;
	u32 fe_fe_frame_id;
	u32 fs_irq_status;
	u32 fe_irq_status;
	u32 le_count;
	u32 len_events;
	u32 len_amount;
	u32 unmatched_events;
	u32 unmatched_amount;
	u8 len_dt;
	u8 len_vc;
	u8 unmatched_dt;
	u8 unmatched_vc;
};

struct csi2_packet_diag {
	u64 fs_total;
	u64 fe_total;
	u64 le_total;
	u64 debug_delta_total;
	u64 incomplete_frames;
	u32 current_packets;
	u64 current_fs_time_ns;
	u32 current_fs_ch_debug;
	u32 current_fs_fe_frame_id;
	u32 current_fs_irq_status;
	u32 current_len_events;
	u32 current_len_amount;
	u32 current_unmatched_events;
	u32 current_unmatched_amount;
	u8 current_len_dt;
	u8 current_len_vc;
	u8 current_unmatched_dt;
	u8 current_unmatched_vc;
	u16 previous_fe_line;
	u32 sample_head;
	u32 sample_count;
	u16 configured_height;
	u8 vc;
	u8 dt;
	bool have_previous_fe;
	bool frame_active;
	struct csi2_packet_diag_sample samples[CSI2_PACKET_DIAG_SAMPLES];
};

struct csi2_error_diag_sample {
	u64 ktime_ns;
	u64 ns_since_fs;
	u32 csi2_status;
	u32 error_type;
	u32 amount;
	u32 ch_debug;
	u32 fe_frame_id;
	u32 configured_height;
	u32 fs_sequence;
	u32 v4l2_sequence;
	u8 dt;
	u8 vc;
	u8 channel;
	u8 frame_active;
};

struct csi2_device {
	/* Parent V4l2 device */
	struct v4l2_device *v4l2_dev;

	void __iomem *base;

	struct dphy_data dphy;

	enum v4l2_mbus_type bus_type;
	unsigned int bus_flags;
	bool multipacket_line;
	unsigned int num_lines[CSI2_NUM_CHANNELS];

	struct media_pad pad[CSI2_NUM_CHANNELS * 2];
	struct v4l2_subdev sd;

	/* lock for csi2 errors counters */
	spinlock_t errors_lock;
	u32 overflows;
	u32 discards_table[DISCARDS_TABLE_NUM_VCS][DISCARDS_TABLE_NUM_ENTRIES];
	u32 discards_dt_table[DISCARDS_TABLE_NUM_ENTRIES];

	/* Diagnostic-only accepted long-packet count between FS and FE_ACK. */
	struct csi2_packet_diag packet_diag[CSI2_NUM_CHANNELS];
	u32 error_diag_head;
	u32 error_diag_count;
	struct csi2_error_diag_sample error_diag[CSI2_ERROR_DIAG_SAMPLES];
};

void csi2_isr(struct csi2_device *csi2, bool *sof, bool *eof);
void csi2_set_buffer(struct csi2_device *csi2, unsigned int channel,
		     dma_addr_t dmaaddr, unsigned int stride,
		     unsigned int size);
void csi2_set_compression(struct csi2_device *csi2, unsigned int channel,
			  enum csi2_compression_mode mode, unsigned int shift,
			  unsigned int offset);
void csi2_start_channel(struct csi2_device *csi2, unsigned int channel,
			enum csi2_mode mode, bool auto_arm,
			bool pack_bytes, unsigned int width,
			unsigned int height);
void csi2_stop_channel(struct csi2_device *csi2, unsigned int channel);
void csi2_open_rx(struct csi2_device *csi2);
void csi2_close_rx(struct csi2_device *csi2);
int csi2_init(struct csi2_device *csi2, struct dentry *debugfs);
void csi2_uninit(struct csi2_device *csi2);

#endif
