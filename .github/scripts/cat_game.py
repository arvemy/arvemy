"""Generate the running-cat banner (light and dark) as animated SVGs.

One 40s "session" of a Chrome-dino-style game: obstacles arrive in an
irregular order, the score counts up, and the run ends in a crash and a
GAME OVER screen before restarting. Everything is precomputed CSS keyframes.
"""

import random
import sys

W, H, GROUND = 840, 170, 146
PX = 3
SPEED = 270  # px/s, obstacles and ground
PERIOD = 40.0  # one session
CRASH_AT = 36.0  # seconds into the session
JUMP_TIME, JUMP_HEIGHT = 0.9, 90
CAT_X = 80
SCORE_RATE = 10  # points per second

CAT_BODY = [
    "...............#...#.",
    "...............##.##.",
    "#..............#####.",
    "#.............##.####",
    ".#............######.",
    "..############.####..",
    "..##############.....",
    "..##############.....",
    "..##############.....",
    "...############......",
]
LEGS_A = ["..##.........##......", ".##...........##.....", "##.............##...."]
LEGS_B = [".....##....##........", ".....##....##........", "....##....##........."]
CAT_W = len(CAT_BODY[0]) * PX
CAT_H = (len(CAT_BODY) + len(LEGS_A)) * PX

CACTUS_SMALL = [
    "...##...", "...##...", "...##.#.", "#..##.#.", "#..####.", "#..##...",
    "####....", "...##...", "...##...", "...##...", "...##...", "...##...",
]
CACTUS_TALL = [
    "....##....", "....##....", "....##..#.", "#...##..#.", "#...##..#.", "#...##..#.",
    "#...#####.", "#...##....", "#####.....", "....##....", "....##....", "....##....",
    "....##....", "....##....", "....##....", "....##....",
]
ROCK = ["...####....", ".#########.", "####.######", "###########", "###########"]
YARN = ["..####..", ".#.#..#.", "#..#.#.#", "#.#..#.#", "#.#.#..#", "#..#.#.#", ".#..#.#.", "..####.."]
BIRD_UP = [
    ".....##......", ".....###.....", ".....####....", "..#######....",
    ".##########..", "#############", "......####...",
]
BIRD_DOWN = [
    "..#######....", ".##########..", "#############", "......####...",
    ".....####....", ".....###.....", ".....##......",
]
CLOUD = ["......####......", "....##....##....", "..##........###.", "##.............#", "################"]
MOON = ["..####..", ".##.....", "##......", "##......", "##......", "##......", ".##.....", "..####.."]


def cluster(*parts, gap=1):
    """Place sprites side by side, bottom-aligned."""
    h = max(len(p) for p in parts)
    rows = []
    for y in range(h):
        row = ""
        for p in parts:
            off = h - len(p)
            row += (p[y - off] if y >= off else "." * len(p[0])) + "." * gap
        rows.append(row)
    return rows


OBSTACLES = {
    "cactus": (CACTUS_SMALL, 0, True),
    "tall": (CACTUS_TALL, 0, True),
    "pair": (cluster(CACTUS_SMALL, CACTUS_SMALL), 0, True),
    "trio": (cluster(CACTUS_SMALL, CACTUS_TALL, CACTUS_SMALL), 0, True),
    "rock": (ROCK, 0, True),
    "yarn": (YARN, 0, True),
    "bird-low": (BIRD_UP, 22, True),
    "bird-high": (BIRD_UP, 62, False),  # cat runs underneath
}


def pixels(grid, ox=0, oy=0):
    return "".join(
        f'<rect x="{ox + x * PX}" y="{oy + y * PX}" width="{PX}" height="{PX}"/>'
        for y, row in enumerate(grid)
        for x, c in enumerate(row)
        if c == "#"
    )


def pct(t):
    return f"{max(0.0, min(100.0, t / PERIOD * 100)):.3f}%"


def schedule(seed=7):
    """Spawn times and kinds; the last one is the cactus the cat crashes into."""
    rng = random.Random(seed)
    kinds = ["cactus", "tall", "pair", "trio", "rock", "yarn", "bird-low", "bird-high"]
    bag, events, t, last = [], [], 1.2, None
    crash_spawn = CRASH_AT - (W - (CAT_X + CAT_W - 6)) / SPEED
    while True:
        # Shuffled bag, so every obstacle type shows up without obvious repeats.
        if not bag:
            bag = rng.sample(kinds, len(kinds))
            if bag[0] == last:
                bag.reverse()
        kind = bag.pop(0)
        sprite, _, _ = OBSTACLES[kind]
        width = len(sprite[0]) * PX
        center = t + (W - (CAT_X + CAT_W / 2 - width / 2)) / SPEED
        if center + JUMP_TIME > CRASH_AT - 0.6:
            break
        events.append((t, kind, center))
        last = kind
        t += rng.uniform(1.25, 2.6)
    return events, crash_spawn


def svg(fg, muted, faint):
    events, crash_spawn = schedule()
    css, body = [], []

    # Obstacles: each has its own keyframes over the whole session.
    for i, (spawn, kind, center) in enumerate(events):
        sprite, lift, _ = OBSTACLES[kind]
        width, height = len(sprite[0]) * PX, len(sprite) * PX
        travel = W + width + 10
        end = spawn + travel / SPEED
        css.append(
            f"@keyframes o{i}{{0%,{pct(spawn)}{{transform:translateX(0)}}"
            f"{pct(end)},100%{{transform:translateX(-{travel}px)}}}}"
            f".o{i}{{animation:o{i} {PERIOD}s linear infinite}}"
        )
        y = GROUND - height + 1 - lift
        if kind.startswith("bird"):
            art = (
                f'<g class="flap-a">{pixels(BIRD_UP)}</g>'
                f'<g class="flap-b">{pixels(BIRD_DOWN)}</g>'
            )
        elif kind == "yarn":
            art = f'<g class="roll">{pixels(sprite)}</g>'
        else:
            art = pixels(sprite)
        body.append(f'<g class="o{i}"><g transform="translate({W}, {y})">{art}</g></g>')

    # The crash: a tall cactus that stops where it meets the cat.
    crash_w = len(CACTUS_TALL[0]) * PX
    stop = W - (CAT_X + CAT_W - 6)
    css.append(
        f"@keyframes crash{{0%,{pct(crash_spawn)}{{transform:translateX(0)}}"
        f"{pct(CRASH_AT)},100%{{transform:translateX(-{stop}px)}}}}"
        f".crash{{animation:crash {PERIOD}s linear infinite}}"
    )
    body.append(
        f'<g class="crash"><g transform="translate({W}, {GROUND - len(CACTUS_TALL) * PX + 1})">'
        f"{pixels(CACTUS_TALL)}</g></g>"
    )

    # Cat jumps: an up/down pair of keyframes per obstacle that needs one.
    frames = ["0%{transform:translateY(0)}"]
    for _, kind, center in events:
        if not OBSTACLES[kind][2]:
            continue
        a, b = center - JUMP_TIME / 2, center + JUMP_TIME / 2
        frames.append(f"{pct(a)}{{transform:translateY(0);animation-timing-function:cubic-bezier(.33,.66,.66,1)}}")
        frames.append(f"{pct(center)}{{transform:translateY(-{JUMP_HEIGHT}px);animation-timing-function:cubic-bezier(.33,0,.66,.34)}}")
        frames.append(f"{pct(b)}{{transform:translateY(0)}}")
    frames.append("100%{transform:translateY(0)}")
    css.append(f"@keyframes jump{{{''.join(frames)}}}.jump{{animation:jump {PERIOD}s infinite}}")

    # Ground specks and clouds scroll until the crash, then freeze.
    rng = random.Random(3)
    ground_len = int(SPEED * CRASH_AT) + W + 40
    specks = "".join(
        f'<rect x="{x}" y="{GROUND + 5 + rng.randint(0, 9)}" width="{rng.choice([2, 4, 6, 8])}" height="2"/>'
        for x in range(0, ground_len, rng.randint(22, 30))
    )
    css.append(
        f"@keyframes ground{{0%{{transform:translateX(0)}}{pct(CRASH_AT)},100%{{transform:translateX(-{int(SPEED * CRASH_AT)}px)}}}}"
        f".ground{{animation:ground {PERIOD}s linear infinite}}"
    )
    cloud_speed = SPEED / 7
    clouds_len = int(cloud_speed * CRASH_AT) + W + 100
    clouds = "".join(
        f'<g transform="translate({x}, {rng.randint(40, 92)})">{pixels(CLOUD)}</g>'
        for x in range(200, clouds_len, 230)
    )
    css.append(
        f"@keyframes clouds{{0%{{transform:translateX(0)}}{pct(CRASH_AT)},100%{{transform:translateX(-{int(cloud_speed * CRASH_AT)}px)}}}}"
        f".clouds{{animation:clouds {PERIOD}s linear infinite}}"
    )

    # Running vs crashed cat, and the GAME OVER overlay.
    css.append(
        f"@keyframes alive{{0%,{pct(CRASH_AT - 0.001)}{{opacity:1}}{pct(CRASH_AT)},100%{{opacity:0}}}}"
        f"@keyframes dead{{0%,{pct(CRASH_AT - 0.001)}{{opacity:0}}{pct(CRASH_AT)},100%{{opacity:1}}}}"
        f".alive{{animation:alive {PERIOD}s steps(1) infinite}}.dead{{opacity:0;animation:dead {PERIOD}s steps(1) infinite}}"
    )

    # Score: each digit is a clipped strip of 0-9 stepped to the right value.
    digit_w, line_h = 13, 22
    score_x, score_y = W - 20 - 5 * digit_w, 18
    digits = []
    final = int(CRASH_AT * SCORE_RATE)
    for place in range(3):
        unit = 10 ** place
        frames, prev = [], None
        for pts in range(0, final + 1):
            v = (pts // unit) % 10
            if v != prev:
                frames.append(f"{pct(pts / SCORE_RATE)}{{transform:translateY(-{v * line_h}px)}}")
                prev = v
        frames.append(f"100%{{transform:translateY(-{prev * line_h}px)}}")
        css.append(f"@keyframes d{place}{{{''.join(frames)}}}.d{place}{{animation:d{place} {PERIOD}s steps(1,end) infinite}}")
        x = score_x + (4 - place) * digit_w
        strip = "".join(f'<text x="{x}" y="{score_y + 16 + n * line_h}">{n}</text>' for n in range(10))
        digits.append(f'<g clip-path="url(#digit{place})"><g class="d{place}">{strip}</g></g>')
    clips = "".join(
        f'<clipPath id="digit{p}"><rect x="{score_x + (4 - p) * digit_w}" y="{score_y}" width="{digit_w}" height="{line_h}"/></clipPath>'
        for p in range(3)
    )
    static_zeros = "".join(f'<text x="{score_x + i * digit_w}" y="{score_y + 16}">0</text>' for i in range(2))

    stars = "".join(
        f'<rect class="twinkle" style="animation-delay:-{rng.uniform(0, 3):.2f}s" x="{rng.choice([rng.randint(200, 300), rng.randint(540, 800)])}" y="{rng.randint(46, 90)}" width="2" height="2"/>'
        for _ in range(9)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Hi, I'm Arvemy - a pixel cat runs, jumps over obstacles and racks up a score">
<defs>{clips}</defs>
<style>
  .fg {{ fill: {fg}; }} .muted {{ fill: {muted}; }} .faint {{ fill: {faint}; }}
  text {{ font: 700 18px ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace; }}
  .title {{ font-size: 20px; letter-spacing: 2px; }}
  .legs-a {{ animation: step .26s steps(1) infinite; }}
  .legs-b {{ animation: step .26s steps(1) infinite -.13s; }}
  .flap-a {{ animation: step .4s steps(1) infinite; }}
  .flap-b {{ animation: step .4s steps(1) infinite -.2s; }}
  .roll {{ transform-box: fill-box; transform-origin: center; animation: roll .6s linear infinite; }}
  .twinkle {{ animation: twinkle 3s ease-in-out infinite; }}
  @keyframes step {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}
  @keyframes roll {{ to {{ transform: rotate(-360deg); }} }}
  @keyframes twinkle {{ 0%, 100% {{ opacity: .2; }} 50% {{ opacity: 1; }} }}
  {''.join(css)}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} .dead {{ opacity: 0; }} }}
</style>
<g class="faint">{stars}<g transform="translate(588, 52)">{pixels(MOON)}</g></g>
<g class="muted"><g class="clouds">{clouds}</g></g>
<text x="{W / 2}" y="34" text-anchor="middle" class="title fg">HI, I'M ARVEMY</text>
<g class="muted"><text x="{score_x - 112}" y="{score_y + 16}">HI 00{final}</text></g>
<g class="fg">{static_zeros}{''.join(digits)}</g>
<g class="fg">
  <rect x="0" y="{GROUND}" width="{W}" height="2"/>
  <g class="ground">{specks}</g>
  {''.join(body)}
  <g class="jump"><g class="alive">
    <g transform="translate({CAT_X}, {GROUND - CAT_H + 2})">{pixels(CAT_BODY)}</g>
    <g class="legs-a" transform="translate({CAT_X}, {GROUND - CAT_H + 2 + len(CAT_BODY) * PX})">{pixels(LEGS_A)}</g>
    <g class="legs-b" transform="translate({CAT_X}, {GROUND - CAT_H + 2 + len(CAT_BODY) * PX})">{pixels(LEGS_B)}</g>
  </g></g>
  <g class="dead">
    <g transform="translate({CAT_X}, {GROUND - CAT_H + 2})">{pixels([r.replace("##.#", "####") if i == 3 else r for i, r in enumerate(CAT_BODY)])}</g>
    <g transform="translate({CAT_X}, {GROUND - CAT_H + 2 + len(CAT_BODY) * PX})">{pixels(LEGS_B)}</g>
    <text x="{CAT_X + 47}" y="{GROUND - CAT_H + 16}" style="font-size:9px" fill="{muted}">x</text>
    <text x="{W / 2}" y="78" text-anchor="middle" class="title" style="letter-spacing:6px">GAME OVER</text>
    <g transform="translate({W / 2 - 18}, 92)">
      <rect x="1.5" y="1.5" width="33" height="29" rx="4" fill="none" stroke="{fg}" stroke-width="3"/>
      <path d="M24 10 a7 7 0 1 0 1.5 7" fill="none" stroke="{fg}" stroke-width="3"/>
      <path d="M20 6 l7 0 l0 7 z"/>
    </g>
  </g>
</g>
</svg>
"""


out = sys.argv[1]
open(f"{out}/cat-game-light.svg", "w").write(svg("#59636e", "#8c959f", "#d1d9e0"))
open(f"{out}/cat-game-dark.svg", "w").write(svg("#9198a1", "#656d76", "#3d444d"))
