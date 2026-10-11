/* raw yuv420p(512x272) -> VP3 호환 Theora 데이터 패킷. 출력: [u32 길이][패킷]... (헤더 패킷 제외)
   사용: venc in.yuv out.pkt W H quality(0~63) keyint [bitrate] */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <theora/theoraenc.h>

static void put(FILE *f, ogg_packet *op) {
  unsigned n = (unsigned)op->bytes;
  unsigned char b[4] = {n >> 24, n >> 16, n >> 8, n};
  fwrite(b, 1, 4, f); fwrite(op->packet, 1, n, f);
}

int main(int argc, char **argv) {
  if (argc < 7) { fprintf(stderr, "usage\n"); return 1; }
  int W = atoi(argv[3]), H = atoi(argv[4]), q = atoi(argv[5]), ki = atoi(argv[6]);
  long br = argc > 7 ? atol(argv[7]) : 0;
  th_info ti; th_info_init(&ti);
  ti.frame_width = W; ti.frame_height = H; ti.pic_width = W; ti.pic_height = H;
  ti.pic_x = 0; ti.pic_y = 0; ti.colorspace = TH_CS_UNSPECIFIED; ti.pixel_fmt = TH_PF_420;
  ti.fps_numerator = 30; ti.fps_denominator = 1; ti.aspect_numerator = 1; ti.aspect_denominator = 1;
  ti.quality = q; ti.target_bitrate = br; ti.keyframe_granule_shift = 6;
  th_enc_ctx *e = th_encode_alloc(&ti);
  if (!e) { fprintf(stderr, "alloc fail\n"); return 1; }
  int v = 1; th_encode_ctl(e, TH_ENCCTL_SET_VP3_COMPATIBLE, &v, sizeof v);
  if (!v) { fprintf(stderr, "vp3 compat refused\n"); return 1; }
  ogg_uint32_t k = ki; th_encode_ctl(e, TH_ENCCTL_SET_KEYFRAME_FREQUENCY_FORCE, &k, sizeof k);
  th_comment tc; th_comment_init(&tc); ogg_packet op;
  while (th_encode_flushheader(e, &tc, &op) > 0) {}
  FILE *fi = fopen(argv[1], "rb"), *fo = fopen(argv[2], "wb");
  size_t ys = (size_t)W * H, cs = ys / 4;
  unsigned char *buf = malloc(ys + 2 * cs);
  th_ycbcr_buffer yb;
  yb[0].width = W; yb[0].height = H; yb[0].stride = W; yb[0].data = buf;
  yb[1].width = W / 2; yb[1].height = H / 2; yb[1].stride = W / 2; yb[1].data = buf + ys;
  yb[2].width = W / 2; yb[2].height = H / 2; yb[2].stride = W / 2; yb[2].data = buf + ys + cs;
  int nf = 0;
  while (fread(buf, 1, ys + 2 * cs, fi) == ys + 2 * cs) {
    if (th_encode_ycbcr_in(e, yb)) { fprintf(stderr, "in fail\n"); return 1; }
    while (th_encode_packetout(e, 0, &op) > 0) put(fo, &op);
    nf++;
  }
  fclose(fo); fprintf(stderr, "frames %d vp3=%d\n", nf, v);
  return 0;
}
