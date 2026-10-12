// Minimal Samsung S5KRC1S V4L2 subdev driver for Raspberry Pi CAM0 bring-up.
// This is a debug driver: it exposes a CSI-2 source endpoint and toggles
// SEL_MODE only. Vendor setfile programming is handled from userspace first.

#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/property.h>

#include <media/media-entity.h>
#include <media/v4l2-async.h>
#include <media/v4l2-common.h>
#include <media/v4l2-ctrls.h>
#include <media/v4l2-fwnode.h>
#include <media/v4l2-subdev.h>

#define S5KRC1S_REG_MODE        0x3000
#define S5KRC1S_MODE_STANDBY    0x00
#define S5KRC1S_MODE_STREAM     0x02
#define S5KRC1S_REG_CCI_ADDR    0x3024

/*
 * In compressed-frame mode, the CSI-2 transport geometry is not the
 * 960x720 sensor coordinate space. The active setfile sends 127 long
 * packets of 8192 bytes between SOF and EOF (MIPI_CSI2_WC=0x2000,
 * MIPI_NUM_OF_PAYLOAD=0x007f). RP1 CFE must use that packet geometry.
 */
#define S5KRC1S_PAYLOAD_BYTES          8192
#define S5KRC1S_MIN_CAPTURE_WIDTH      8192
#define S5KRC1S_MAX_CAPTURE_WIDTH      8256
#define S5KRC1S_MIN_CAPTURE_HEIGHT     126
#define S5KRC1S_MAX_CAPTURE_HEIGHT     160
#define S5KRC1S_DEFAULT_HEIGHT         127

static long link_freq_hz = 400000000;
module_param(link_freq_hz, long, 0644);
MODULE_PARM_DESC(link_freq_hz, "CSI-2 link frequency in Hz; lane bit rate is 2x this value");

static int csi2_dt = 0x31;
module_param(csi2_dt, int, 0644);
MODULE_PARM_DESC(csi2_dt, "CSI-2 data type advertised to the receiver, e.g. 0x31 user-defined or 0x2a RAW8");

static s64 s5krc1s_link_freq_menu[] = {
	400000000LL,
};

struct s5krc1s {
	struct i2c_client *client;
	struct v4l2_subdev sd;
	struct media_pad pad;
	struct v4l2_ctrl_handler ctrls;
	struct v4l2_mbus_framefmt fmt;
	struct mutex lock;
	unsigned int num_data_lanes;
	s64 pixel_rate;
	u8 csi2_dt;
};

static inline struct s5krc1s *to_s5krc1s(struct v4l2_subdev *sd)
{
	return container_of(sd, struct s5krc1s, sd);
}

static int s5krc1s_read8(struct i2c_client *client, u16 reg, u8 *val)
{
	u8 addr[2] = { reg >> 8, reg & 0xff };
	struct i2c_msg msg[2] = {
		{
			.addr = client->addr,
			.flags = 0,
			.len = 2,
			.buf = addr,
		},
		{
			.addr = client->addr,
			.flags = I2C_M_RD,
			.len = 1,
			.buf = val,
		},
	};
	int ret = i2c_transfer(client->adapter, msg, 2);

	return ret == 2 ? 0 : (ret < 0 ? ret : -EIO);
}

static int s5krc1s_write8(struct i2c_client *client, u16 reg, u8 val)
{
	u8 buf[3] = { reg >> 8, reg & 0xff, val };
	struct i2c_msg msg = {
		.addr = client->addr,
		.flags = 0,
		.len = sizeof(buf),
		.buf = buf,
	};
	int ret = i2c_transfer(client->adapter, &msg, 1);

	return ret == 1 ? 0 : (ret < 0 ? ret : -EIO);
}

static int s5krc1s_s_stream(struct v4l2_subdev *sd, int enable)
{
	struct s5krc1s *s5k = to_s5krc1s(sd);
	u8 mode = enable ? S5KRC1S_MODE_STREAM : S5KRC1S_MODE_STANDBY;
	int ret;

	mutex_lock(&s5k->lock);
	ret = s5krc1s_write8(s5k->client, S5KRC1S_REG_MODE, mode);
	mutex_unlock(&s5k->lock);

	dev_info(&s5k->client->dev, "s_stream(%d), mode=0x%02x ret=%d\n",
		 enable, mode, ret);
	return ret;
}

static int s5krc1s_enum_mbus_code(struct v4l2_subdev *sd,
				  struct v4l2_subdev_state *state,
				  struct v4l2_subdev_mbus_code_enum *code)
{
	if (code->index)
		return -EINVAL;

	code->code = MEDIA_BUS_FMT_Y8_1X8;
	return 0;
}

static int s5krc1s_enum_frame_size(struct v4l2_subdev *sd,
				   struct v4l2_subdev_state *state,
				   struct v4l2_subdev_frame_size_enum *fse)
{
	if (fse->index || fse->code != MEDIA_BUS_FMT_Y8_1X8)
		return -EINVAL;

	fse->min_width = S5KRC1S_MIN_CAPTURE_WIDTH;
	fse->max_width = S5KRC1S_MAX_CAPTURE_WIDTH;
	fse->min_height = S5KRC1S_MIN_CAPTURE_HEIGHT;
	fse->max_height = S5KRC1S_MAX_CAPTURE_HEIGHT;
	return 0;
}

static int s5krc1s_get_fmt(struct v4l2_subdev *sd,
			   struct v4l2_subdev_state *state,
			   struct v4l2_subdev_format *fmt)
{
	struct s5krc1s *s5k = to_s5krc1s(sd);

	mutex_lock(&s5k->lock);
	fmt->format = s5k->fmt;
	mutex_unlock(&s5k->lock);
	return 0;
}

static int s5krc1s_set_fmt(struct v4l2_subdev *sd,
			   struct v4l2_subdev_state *state,
			   struct v4l2_subdev_format *fmt)
{
	struct s5krc1s *s5k = to_s5krc1s(sd);
	unsigned int width = fmt->format.width;
	unsigned int height = fmt->format.height;

	if (width < S5KRC1S_MIN_CAPTURE_WIDTH)
		width = S5KRC1S_MIN_CAPTURE_WIDTH;
	if (width > S5KRC1S_MAX_CAPTURE_WIDTH)
		width = S5KRC1S_MAX_CAPTURE_WIDTH;
	if (height < S5KRC1S_MIN_CAPTURE_HEIGHT)
		height = S5KRC1S_MIN_CAPTURE_HEIGHT;
	if (height > S5KRC1S_MAX_CAPTURE_HEIGHT)
		height = S5KRC1S_MAX_CAPTURE_HEIGHT;
	width = (width + 15U) & ~15U;
	if (width > S5KRC1S_MAX_CAPTURE_WIDTH)
		width = S5KRC1S_MAX_CAPTURE_WIDTH;

	fmt->format.code = MEDIA_BUS_FMT_Y8_1X8;
	fmt->format.width = width;
	fmt->format.height = height;
	fmt->format.field = V4L2_FIELD_NONE;
	fmt->format.colorspace = V4L2_COLORSPACE_RAW;

	mutex_lock(&s5k->lock);
	s5k->fmt = fmt->format;
	mutex_unlock(&s5k->lock);
	return 0;
}

static int s5krc1s_get_frame_desc(struct v4l2_subdev *sd, unsigned int pad,
				  struct v4l2_mbus_frame_desc *fd)
{
	struct s5krc1s *s5k = to_s5krc1s(sd);

	if (pad)
		return -EINVAL;

	fd->type = V4L2_MBUS_FRAME_DESC_TYPE_CSI2;
	fd->num_entries = 1;
	fd->entry[0].stream = 0;
	fd->entry[0].pixelcode = MEDIA_BUS_FMT_Y8_1X8;
	fd->entry[0].flags = V4L2_MBUS_FRAME_DESC_FL_LEN_MAX |
			     V4L2_MBUS_FRAME_DESC_FL_BLOB;
	fd->entry[0].length = s5k->fmt.width * s5k->fmt.height;
	fd->entry[0].bus.csi2.vc = 0;
	fd->entry[0].bus.csi2.dt = to_s5krc1s(sd)->csi2_dt;
	return 0;
}

static int s5krc1s_get_mbus_config(struct v4l2_subdev *sd, unsigned int pad,
				   struct v4l2_mbus_config *cfg)
{
	cfg->type = V4L2_MBUS_CSI2_DPHY;
	cfg->bus.mipi_csi2.num_data_lanes = to_s5krc1s(sd)->num_data_lanes;
	return 0;
}

static const struct v4l2_subdev_video_ops s5krc1s_video_ops = {
	.s_stream = s5krc1s_s_stream,
};

static const struct v4l2_subdev_pad_ops s5krc1s_pad_ops = {
	.enum_mbus_code = s5krc1s_enum_mbus_code,
	.enum_frame_size = s5krc1s_enum_frame_size,
	.get_fmt = s5krc1s_get_fmt,
	.set_fmt = s5krc1s_set_fmt,
	.get_frame_desc = s5krc1s_get_frame_desc,
	.get_mbus_config = s5krc1s_get_mbus_config,
};

static const struct v4l2_subdev_ops s5krc1s_subdev_ops = {
	.video = &s5krc1s_video_ops,
	.pad = &s5krc1s_pad_ops,
};

static int s5krc1s_probe(struct i2c_client *client)
{
	struct s5krc1s *s5k;
	struct fwnode_handle *endpoint;
	struct v4l2_fwnode_endpoint ep = {
		.bus_type = V4L2_MBUS_CSI2_DPHY,
	};
	u8 cci = 0, mode = 0;
	int ret;

	s5k = devm_kzalloc(&client->dev, sizeof(*s5k), GFP_KERNEL);
	if (!s5k)
		return -ENOMEM;

	s5k->client = client;
	s5k->num_data_lanes = 4;
	mutex_init(&s5k->lock);

	endpoint = fwnode_graph_get_next_endpoint(dev_fwnode(&client->dev), NULL);
	if (endpoint) {
		ret = v4l2_fwnode_endpoint_parse(endpoint, &ep);
		fwnode_handle_put(endpoint);
		if (!ret && ep.bus.mipi_csi2.num_data_lanes)
			s5k->num_data_lanes = ep.bus.mipi_csi2.num_data_lanes;
	}

	if (link_freq_hz < 40000000 || link_freq_hz > 1250000000)
		return dev_err_probe(&client->dev, -EINVAL,
				     "invalid link_freq_hz=%ld\n", link_freq_hz);
	if (csi2_dt < 0 || csi2_dt > 0x3f)
		return dev_err_probe(&client->dev, -EINVAL,
				     "invalid csi2_dt=0x%x\n", csi2_dt);

	s5krc1s_link_freq_menu[0] = link_freq_hz;
	s5k->pixel_rate = link_freq_hz * 2 * s5k->num_data_lanes / 8;
	s5k->csi2_dt = csi2_dt;

	ret = s5krc1s_read8(client, S5KRC1S_REG_CCI_ADDR, &cci);
	if (ret)
		return dev_err_probe(&client->dev, ret,
				     "failed to read CCI address register\n");

	ret = s5krc1s_read8(client, S5KRC1S_REG_MODE, &mode);
	if (ret)
		return dev_err_probe(&client->dev, ret,
				     "failed to read mode register\n");

	s5k->fmt.width = S5KRC1S_MIN_CAPTURE_WIDTH;
	s5k->fmt.height = S5KRC1S_DEFAULT_HEIGHT;
	s5k->fmt.code = MEDIA_BUS_FMT_Y8_1X8;
	s5k->fmt.field = V4L2_FIELD_NONE;
	s5k->fmt.colorspace = V4L2_COLORSPACE_RAW;

	v4l2_i2c_subdev_init(&s5k->sd, client, &s5krc1s_subdev_ops);
	s5k->sd.flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;
	s5k->sd.entity.function = MEDIA_ENT_F_CAM_SENSOR;
	s5k->pad.flags = MEDIA_PAD_FL_SOURCE;

	v4l2_ctrl_handler_init(&s5k->ctrls, 2);
	v4l2_ctrl_new_int_menu(&s5k->ctrls, NULL, V4L2_CID_LINK_FREQ,
			       ARRAY_SIZE(s5krc1s_link_freq_menu) - 1, 0,
			       s5krc1s_link_freq_menu);
	v4l2_ctrl_new_std(&s5k->ctrls, NULL, V4L2_CID_PIXEL_RATE,
			  s5k->pixel_rate, s5k->pixel_rate, 1,
			  s5k->pixel_rate);
	if (s5k->ctrls.error) {
		ret = s5k->ctrls.error;
		dev_err(&client->dev, "control init failed: %d\n", ret);
		goto err_ctrls;
	}
	s5k->sd.ctrl_handler = &s5k->ctrls;

	ret = media_entity_pads_init(&s5k->sd.entity, 1, &s5k->pad);
	if (ret)
		goto err_ctrls;

	ret = v4l2_async_register_subdev_sensor(&s5k->sd);
	if (ret) {
		goto err_media;
	}

	dev_info(&client->dev,
		 "S5KRC1S debug subdev registered, cci=0x%02x mode=0x%02x lanes=%u link_freq=%lld pixel_rate=%lld csi2_dt=0x%02x\n",
		 cci, mode, s5k->num_data_lanes, s5krc1s_link_freq_menu[0],
		 s5k->pixel_rate, s5k->csi2_dt);
	return 0;

err_media:
	media_entity_cleanup(&s5k->sd.entity);
err_ctrls:
	v4l2_ctrl_handler_free(&s5k->ctrls);
	return ret;
}

static void s5krc1s_remove(struct i2c_client *client)
{
	struct v4l2_subdev *sd = i2c_get_clientdata(client);
	struct s5krc1s *s5k = to_s5krc1s(sd);

	v4l2_async_unregister_subdev(sd);
	media_entity_cleanup(&sd->entity);
	v4l2_ctrl_handler_free(&s5k->ctrls);
}

static const struct of_device_id s5krc1s_of_match[] = {
	{ .compatible = "samsung,s5krc1s" },
	{ }
};
MODULE_DEVICE_TABLE(of, s5krc1s_of_match);

static struct i2c_driver s5krc1s_i2c_driver = {
	.driver = {
		.name = "s5krc1s_min",
		.of_match_table = s5krc1s_of_match,
	},
	.probe = s5krc1s_probe,
	.remove = s5krc1s_remove,
};

module_i2c_driver(s5krc1s_i2c_driver);

MODULE_DESCRIPTION("Minimal Samsung S5KRC1S debug V4L2 subdev driver");
MODULE_AUTHOR("OSDA bring-up");
MODULE_LICENSE("GPL");
