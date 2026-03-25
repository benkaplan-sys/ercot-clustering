"""Dendrogram visualization for hierarchical clustering results.

The dendrogram shows the full tree structure of the clustering, including the
distances at which nodes and clusters merge.  It is most useful for selecting
an appropriate distance threshold and for understanding how many natural
clusters exist in the data.

For large datasets (N > 200 nodes) the full dendrogram becomes unreadable;
in those cases use ``truncate_mode="lastp"`` to show only the top *p* merge
levels.
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.cluster.hierarchy import dendrogram

logger = logging.getLogger(__name__)


def plot_dendrogram(
    linkage_matrix: np.ndarray,
    labels: list[str] | None = None,
    title: str = "Hierarchical Clustering Dendrogram",
    distance_threshold: float | None = None,
    truncate_mode: str | None = None,
    p: int = 30,
    output_path: Path | None = None,
    figsize: tuple[float, float] = (16, 6),
) -> plt.Figure:
    """Plot a dendrogram from a scipy linkage matrix.

    Args:
        linkage_matrix: Linkage array of shape ``(N-1, 4)`` as returned by
            ``scipy.cluster.hierarchy.linkage``.
        labels: Optional list of leaf labels (node names).  If None, numeric
            indices are used.
        title: Figure title.
        distance_threshold: If provided, draw a horizontal dashed line at this
            distance to indicate where the tree would be cut.
        truncate_mode: Passed to ``scipy.cluster.hierarchy.dendrogram``.  Use
            ``"lastp"`` to show only the top *p* merge levels.
        p: Number of merge levels shown when *truncate_mode="lastp"*.
        output_path: If provided, save the figure to this path.
        figsize: Matplotlib figure size ``(width, height)`` in inches.

    Returns:
        The Matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=figsize)

    dend_kwargs: dict = {
        "ax": ax,
        "leaf_rotation": 90,
        "leaf_font_size": 6,
        "color_threshold": distance_threshold if distance_threshold is not None else 0,
    }
    if labels is not None:
        dend_kwargs["labels"] = labels
    if truncate_mode is not None:
        dend_kwargs["truncate_mode"] = truncate_mode
        dend_kwargs["p"] = p

    dendrogram(linkage_matrix, **dend_kwargs)

    if distance_threshold is not None:
        ax.axhline(
            y=distance_threshold,
            color="red",
            linestyle="--",
            linewidth=1.5,
            label=f"Cut threshold = {distance_threshold}",
        )
        ax.legend(fontsize=9)

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Node" if labels else "Node index")
    ax.set_ylabel("Distance (1 − ρ)")
    fig.tight_layout()

    if output_path is not None:
        output_path = Path(output_path)
        logger.info("Saving dendrogram to %s", output_path)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")

    return fig
