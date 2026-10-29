// Soup engine: runs random 16x16 soups of a Life-like rule until periodic.
// Escaping objects (beyond radius R from the soup) are cut out and printed.
// Usage: soup <rule e.g. b3s23> [maxspan] [maxgen] < lines of "<index> <sha256-hex of seed>"
// A stdin line "R <rule>" switches rule (echoed as "R <rule>"), for batch screening.
// Output lines:
//   S <idx> <period> <gen> <n> x y x y ...   (final periodic state)
//   E <idx> <gen> <n> x y ...                (ejected component)
//   U <idx> <gen> <n>                        (never stabilized: possible gun/puffer)
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define N 1024
#define C (N / 2)
#define R 80
#define MAXGEN 15000
static int maxgen = MAXGEN, maxspan = 300;  // optional argv[2], argv[3]
static long maxpop = 1L << 40, pop;           // optional argv[4]: give up (U) above this population
static long maxwork = 1L << 60;               // optional argv[5]: give up after this many cell-generations
#define MAXP 240
#define SOUP 16

static uint8_t A[N * N], B[N * N];
static uint64_t H[MAXGEN + 1];
static int birth[9], survive[9];
static int x0, x1, y0, y1;  // bbox of live cells (inclusive)

static uint64_t mix(uint64_t z) {
  z += 0x9e3779b97f4a7c15ULL;
  z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
  z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
  return z ^ (z >> 31);
}

static uint64_t step(uint8_t *src, uint8_t *dst) {
  int nx0 = N, nx1 = -1, ny0 = N, ny1 = -1;
  uint64_t h = 0;
  pop = 0;
  for (int y = y0 - 1; y <= y1 + 1; y++) {
    uint8_t *u = src + (y - 1) * N, *m = src + y * N, *d = src + (y + 1) * N;
    uint8_t *o = dst + y * N;
    for (int x = x0 - 1; x <= x1 + 1; x++) {
      int n = u[x - 1] + u[x] + u[x + 1] + m[x - 1] + m[x + 1] + d[x - 1] + d[x] + d[x + 1];
      int v = m[x] ? survive[n] : birth[n];
      o[x] = v;
      if (v) {
        pop++;
        if (x < nx0) nx0 = x;
        if (x > nx1) nx1 = x;
        if (y < ny0) ny0 = y;
        if (y > ny1) ny1 = y;
        h += mix(((uint64_t)y << 20) | (uint64_t)x);
      }
    }
  }
  // clear the stale ring outside the new region in src is unnecessary; dst ring
  // beyond bbox+1 was zero already because live cells never exceed bbox+1.
  x0 = nx0; x1 = nx1; y0 = ny0; y1 = ny1;
  return h;
}

static int stk[N * 64];

#define SG 160
static uint8_t SA[SG * SG], SB[SG * SG];

static void snorm(const int *c, int n, int *out, int *ox, int *oy) {
  int mx = 1 << 30, my = 1 << 30;
  for (int i = 0; i < n; i++) { if (c[2*i] < mx) mx = c[2*i]; if (c[2*i+1] < my) my = c[2*i+1]; }
  for (int i = 0; i < n; i++) { out[2*i] = c[2*i] - mx; out[2*i+1] = c[2*i+1] - my; }
  *ox = mx; *oy = my;
}

// Evolve a small component alone; true if it is a spaceship (returns translated).
static int is_ship(const int *cells, int nc) {
  if (nc > 80) return 0;
  static int ref[200], cur[4000], nr[4000];
  int rx, ry;
  snorm(cells, nc, ref, &rx, &ry);
  static int refs[200];
  for (int i = 0; i < nc; i++) { refs[2*i] = ref[2*i]; refs[2*i+1] = ref[2*i+1]; }
  for (int i = 1; i < nc; i++)  // insertion sort by (y, x) to match scan order
    for (int j = i; j > 0 && (refs[2*j+1] < refs[2*j-1] || (refs[2*j+1] == refs[2*j-1] && refs[2*j] < refs[2*j-2])); j--) {
      int tx = refs[2*j], ty = refs[2*j+1];
      refs[2*j] = refs[2*j-2]; refs[2*j+1] = refs[2*j-1]; refs[2*j-2] = tx; refs[2*j-1] = ty;
    }
  memset(SA, 0, sizeof SA);
  for (int i = 0; i < nc; i++) {
    int x = ref[2*i] + 48, y = ref[2*i+1] + 48;
    if (x < 1 || x >= SG - 1 || y < 1 || y >= SG - 1) return 0;
    SA[y * SG + x] = 1;
  }
  uint8_t *a = SA, *b = SB;
  memset(SB, 0, sizeof SB);
  int lx = 47, hx = 48 + 40, ly = 47, hy = 48 + 40;
  for (int g = 1; g <= 48; g++) {
    int n = 0, nlx = SG, nhx = 0, nly = SG, nhy = 0;
    for (int y = ly; y <= hy; y++)
      for (int x = lx; x <= hx; x++) {
        int k = y * SG + x;
        int s = a[k-SG-1]+a[k-SG]+a[k-SG+1]+a[k-1]+a[k+1]+a[k+SG-1]+a[k+SG]+a[k+SG+1];
        int v = a[k] ? survive[s] : birth[s];
        b[k] = v;
        if (v) {
          if (n >= 2000 || x < 2 || x >= SG - 2 || y < 2 || y >= SG - 2) return 0;
          cur[2*n] = x; cur[2*n+1] = y; n++;
          if (x < nlx) nlx = x;
          if (x > nhx) nhx = x;
          if (y < nly) nly = y;
          if (y > nhy) nhy = y;
        }
      }
    if (!n) return 0;
    for (int y = ly; y <= hy; y++) memset(a + y * SG + lx, 0, hx - lx + 1);
    lx = nlx - 1; hx = nhx + 1; ly = nly - 1; hy = nhy + 1;
    uint8_t *t = a; a = b; b = t;
    if (n != nc) continue;
    int ox, oy;
    snorm(cur, n, nr, &ox, &oy);
    if (memcmp(nr, refs, sizeof(int) * 2 * nc) == 0) return ox != 48 || oy != 48;
  }
  return 0;
}

// Remove spaceships that wandered beyond radius R (or anything near the grid edge); print them.
static void eject(uint8_t *g, long idx, int gen) {
  if (x0 > C - R && x1 < C + R && y0 > C - R && y1 < C + R) return;
  static int cells[200000];
  static int kept[N * 64];
  int nkept = 0;
  for (int y = y0; y <= y1; y++)
    for (int x = x0; x <= x1; x++) {
      if (g[y * N + x] != 1) continue;
      if (x > C - R && x < C + R && y > C - R && y < C + R) continue;
      int sp = 0, nc = 0, force = 0;
      stk[sp++] = y * N + x;
      g[y * N + x] = 2;
      while (sp) {
        int p = stk[--sp];
        int py = p / N, px = p % N;
        if (px < 64 || px >= N - 64 || py < 64 || py >= N - 64) force = 1;
        if (nc < 100000) { cells[2 * nc] = px; cells[2 * nc + 1] = py; nc++; }
        for (int dy = -2; dy <= 2; dy++)
          for (int dx = -2; dx <= 2; dx++) {
            int q = (py + dy) * N + px + dx;
            if (g[q] == 1 && sp < N * 64) { g[q] = 2; stk[sp++] = q; }
          }
      }
      if (force || is_ship(cells, nc)) {
        printf("E %ld %d %d", idx, gen, nc);
        for (int i = 0; i < nc; i++) {
          g[cells[2 * i + 1] * N + cells[2 * i]] = 0;
          printf(" %d %d", cells[2 * i] - C, cells[2 * i + 1] - C);
        }
        printf("\n");
      } else {
        for (int i = 0; i < nc && nkept < N * 64; i++) kept[nkept++] = cells[2 * i + 1] * N + cells[2 * i];
      }
    }
  for (int i = 0; i < nkept; i++) g[kept[i]] = 1;
  // recompute bbox
  int nx0 = N, nx1 = -1, ny0 = N, ny1 = -1;
  for (int y = y0; y <= y1; y++)
    for (int x = x0; x <= x1; x++)
      if (g[y * N + x]) {
        if (x < nx0) nx0 = x;
        if (x > nx1) nx1 = x;
        if (y < ny0) ny0 = y;
        if (y > ny1) ny1 = y;
      }
  x0 = nx0; x1 = nx1; y0 = ny0; y1 = ny1;
}

static uint64_t hashgrid(uint8_t *g) {
  uint64_t h = 0;
  for (int y = y0; y <= y1; y++)
    for (int x = x0; x <= x1; x++)
      if (g[y * N + x]) h += mix(((uint64_t)y << 20) | (uint64_t)x);
  return h;
}

static void parse_rule(const char *r) {
  memset(birth, 0, sizeof birth);
  memset(survive, 0, sizeof survive);
  int *cur = 0;
  for (const char *p = r; *p; p++) {
    if (*p == 'b' || *p == 'B') cur = birth;
    else if (*p == 's' || *p == 'S') cur = survive;
    else if (*p >= '0' && *p <= '8' && cur) cur[*p - '0'] = 1;
  }
}

int main(int argc, char **argv) {
  if (argc < 2) { fprintf(stderr, "usage: soup rule < seeds\n"); return 1; }
  parse_rule(argv[1]);
  uint64_t pre = 1469598103934665603ULL;
  for (const char *p = argv[1]; *p; p++) pre = (pre ^ (uint8_t)*p) * 1099511628211ULL;
  (void)pre;
  static int out[2 * N * 64];
  if (argc > 2) maxspan = atoi(argv[2]);
  if (argc > 4) maxpop = atol(argv[4]);
  if (argc > 5) maxwork = atol(argv[5]);
  if (argc > 3) maxgen = atoi(argv[3]) < MAXGEN ? atoi(argv[3]) : MAXGEN;
  long idx;
  char hex[80], line[256];
  // stdin: "<index> <sha256 hex of seed>" per soup (apgsearch C1 hashsoup layout)
  while (fgets(line, sizeof line, stdin)) {
    if (line[0] == 'R') {
      char r[64];
      if (sscanf(line + 1, "%63s", r) == 1) { parse_rule(r); printf("R %s\n", r); fflush(stdout); }
      continue;
    }
    if (sscanf(line, "%ld %70s", &idx, hex) != 2) continue;
    memset(A, 0, sizeof A);
    memset(B, 0, sizeof B);
    for (int j = 0; j < 32; j++) {
      unsigned v;
      sscanf(hex + 2 * j, "%2x", &v);
      int y = j / 2, xb = (j % 2) ? 0 : 8;
      for (int b = 0; b < 8; b++) A[(C + y) * N + C + xb + b] = (v >> b) & 1;
    }
    x0 = C; x1 = C + SOUP - 1; y0 = C; y1 = C + SOUP - 1;
    uint8_t *cur = A, *nxt = B;
    H[0] = hashgrid(cur);
    int done = 0, gen;
    long work = 0;
    for (gen = 1; gen <= maxgen && !done; gen++) {
      if (x1 < 0) { printf("S %ld 1 %d 0\n", idx, gen); done = 1; break; }
      int ox0 = x0, ox1 = x1, oy0 = y0, oy1 = y1;
      H[gen] = step(cur, nxt);
      // clear the previous generation so the buffer is clean for reuse
      for (int y = oy0; y <= oy1; y++) memset(cur + y * N + ox0, 0, ox1 - ox0 + 1);
      uint8_t *t = cur; cur = nxt; nxt = t;
      if (gen % 8 == 0) {
        if (!(x0 > C - R && x1 < C + R && y0 > C - R && y1 < C + R)) {
          eject(cur, idx, gen);
          H[gen] = hashgrid(cur);
          // history before ejection is not comparable; reset by poisoning
          for (int k = (gen > MAXP * 2 ? gen - MAXP * 2 : 0); k < gen; k++) H[k] = ~(uint64_t)k * 7919;
        }
      }
      if (x1 < 0) { printf("S %ld 1 %d 0\n", idx, gen); done = 1; break; }
      if (x1 - x0 > maxspan || y1 - y0 > maxspan) break;  // still-growing mess
      work += pop;
      if (pop > maxpop || work > maxwork) break;
#ifdef DEBUG
      if (gen % 1000 == 0) fprintf(stderr, "gen %d bbox %d..%d x %d..%d\n", gen, x0 - C, x1 - C, y0 - C, y1 - C);
#endif
      if (gen < 2 * MAXP && gen % 4) continue;
      for (int p = 1; p <= MAXP && 2 * p <= gen; p++) {
        if (H[gen] != H[gen - p]) continue;
        int ok = 1;
        for (int k = 1; k <= p && ok; k++) ok = H[gen - k] == H[gen - p - k];
        if (!ok) continue;
        int n = 0;
        for (int y = y0; y <= y1; y++)
          for (int x = x0; x <= x1; x++)
            if (cur[y * N + x] && n < N * 64) { out[2 * n] = x - C; out[2 * n + 1] = y - C; n++; }
        printf("S %ld %d %d %d", idx, p, gen, n);
        for (int i = 0; i < n; i++) printf(" %d %d", out[2 * i], out[2 * i + 1]);
        printf("\n");
        done = 1;
        break;
      }
    }
    if (!done) {
      int n = 0;
      for (int y = y0; y <= y1; y++)
        for (int x = x0; x <= x1; x++) n += cur[y * N + x];
      printf("U %ld %d %d\n", idx, gen, n);
    }
  }
  return 0;
}
