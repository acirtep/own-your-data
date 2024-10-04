from enum import Enum

DEFAULT_METRIC_COLUMN = "Just-Count"


class SupportedPlots(str, Enum):
    bar = "bar"
    line = "line"
    sankey = "sankey"
    heatmap = "heatmap"

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))
