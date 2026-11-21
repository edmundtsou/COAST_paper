"""Fig. 6 on the same canvas and in the same order as Fig. 5 (scripts/fig5_figure.py), with control and AKI
in place of mouse and human:
 a  one control and one IR section, PT tubules coloured by pseudostructure
 b  Havcr1 (KIM-1) expression in the same tubules
 c  Havcr1 against pseudostructure: binned means (points) and fitted curves (lines) in log2(CP10k + 0.5)
 d  the transporter handoff pairs of Fig. 5d, control against AKI, in counts with each arm's switch (poster)
 e  three genes whose healthy within-segment gradient injury erases (Cyp4a14, Agt, Cyp24a1)
 f  the four gene shape clusters of shape_clusters.py: mean z-scored shape per section and per condition
 g  one called pathway per pathway group, drawn as in f
Writes fig6.png, fig6.pdf and fig6_wireframe.png to <results-root>/paper_figures/fig6/.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig5_figure as F  # noqa: E402
from fig5_panels import XRANGE  # noqa: E402
from fig6_panels import CONTROLS, CTRL, INJURED, IR, MICE, reference_x  # noqa: E402

LEAD = 'Havcr1'
# e: healthy within-segment gradients injury erases (Category A examples; the controls carry the gradient)
GENES_E = ['Cyp4a14', 'Agt', 'Cyp24a1']
# f: genes named on each shape cluster; g: per pathway group, the called set with the smallest competitive p
# (COAST fit: f keeps the earlier named genes that are still in a cluster, otherwise its two largest changes)
# d: the transporter handoff pairs of Fig. 5d (fig5_figure.D_PAIRS), control against AKI (user, 2026-11-16), in counts
# as on the control-vs-AKI poster (counts per 10,000, switch where the count curves cross); both arms share one probe
# panel, so counts compare directly. The crossing moves with partner levels, which is the poster's reading
# f: two named genes per class; g: called sets for the S3 story: proliferation rises (E2F), respiration (TCA cycle),
# lysosome (protein reabsorption) and peroxisome (fatty acid oxidation) are lost from S3
EXAMPLES = {1: ['Cyp4a14', 'Abcb1b'], 2: ['Hmox1', 'Cdk2'], 3: ['Slc6a13', 'Slc22a12'], 4: ['Havcr1', 'Slc22a2']}
HIGHLIGHT = ['MSigDB_Hallmark_2020::E2F Targets',
             'Reactome_2022::Citric Acid (TCA) Cycle And Respiratory Electron Transport R-HSA-1428517',
             'KEGG_2019_Mouse::Lysosome', 'KEGG_2019_Mouse::Peroxisome']
SHADE = {'Ctrl1A2': CTRL, 'Ctrl1A4': '#7FA8D8', 'IR2A2': IR, 'IR2A4': '#F0A978'}
KEY = {'Ctrl1A2': 'Control 1', 'Ctrl1A4': 'Control 2', 'IR2A2': 'AKI 1', 'IR2A4': 'AKI 2'}
EARLY = {'control': '#3A8DD0', 'AKI': '#F0A978'}
LATE = {'control': '#1B3A5C', 'AKI': '#8A3B08'}
GROUPS = {'control': (CONTROLS, CTRL, EARLY['control'], LATE['control']),
          'AKI': (INJURED, IR, EARLY['AKI'], LATE['AKI'])}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--results-root', default=str(REPO / 'results'))
    p.add_argument('--screen', default='screen', help='screen folder under paper_figures/fig6')
    return p.parse_args(argv)


def load(screen: Path):
    """curves.npz holds the genes the screen kept, with the bins Fig. 5's curve panels draw."""
    z = np.load(screen / 'curves.npz', allow_pickle=True)
    names = list(z['genes'])
    pos = {g: i for i, g in enumerate(names)}
    curves = {m: {part: z[f'{part}|{m}'] for part in ('curve', 'bins', 'bin_x')} for m in MICE}
    return z['grid'], curves, pos


def main(argv=None):
    args = parse_args(argv)
    rroot = Path(args.results_root)
    root = rroot / 'paper_figures/fig6'
    screen = root / args.screen
    plt = F.style()
    from matplotlib.colors import LinearSegmentedColormap
    F.EXPR_CMAP = LinearSegmentedColormap.from_list('expr', ['#FBEDE2', '#D9692B', '#4A1D02'])
    grid, curves, pos = load(screen)
    axes = pd.read_csv(screen / 'axes.csv')
    b12, b23 = float(axes.b12.iloc[0]), float(axes.b23.iloc[0])
    # each mouse's drawn range: the sampled range of the handoff genes' axis (axes.csv carries no x range here)
    XRANGE.update({m: (float(curves[m]['bin_x'][pos[LEAD]].min()), float(curves[m]['bin_x'][pos[LEAD]].max()))
                   for m in MICE})

    W, H = 180, 238
    fig, R, panel, boxes = F.canvas(plt, W, H)
    panel('a', 1, 1, 89, 50)
    panel('b', 91, 1, 179, 50)
    F.panel_maps(fig, rroot, R(8, 7, 78, 34, rect=True), R(98, 7, 78, 34, rect=True), run='aki',
                 shown=(('Ctrl1A2', 'control'), ('IR2A2', 'AKI')), gene=LEAD, pt=reference_x(rroot))
    # examples by the stated rules from the current shape clusters (fig56_examples.py)
    from fig56_examples import pick
    # g: per pathway group the HIGHLIGHT set while it is still called, else the called set with the smallest p
    _, examples, highlight = pick(root / 'shape_clusters', [], EXAMPLES, HIGHLIGHT)
    print('examples: d', F.D_PAIRS, '| f', examples, '| g', highlight, flush=True)
    F.curve_rows(fig, R, panel, curves, pos, grid, b12, b23, LEAD, F.D_PAIRS, GENES_E, MICE, SHADE, KEY, GROUPS,
                 counts_d=True)
    F.shape_rows(fig, R, panel, root / 'shape_clusters', GROUPS, SHADE, b12, b23, highlight, examples)
    fig.savefig(root / 'fig6.png', facecolor='white', dpi=400)
    fig.savefig(root / 'fig6.pdf', facecolor='white')
    plt.close(fig)
    F.wireframe(plt, W, H, boxes, root / 'fig6_wireframe.png')


if __name__ == '__main__':
    main()
