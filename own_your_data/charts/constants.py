from enum import Enum


class ExtendedEnum(Enum):

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class SupportedPlots(str, ExtendedEnum):
    bar = "bar"
    line = "line"
    heatmap = "heatmap"
    scatter = "scatter"
    sankey = "sankey"
    world_map = "world-map"
    pie = "pie"


class SupportedAggregationMethods(str, ExtendedEnum):
    sum = "sum"
    count = "count"
    avg = "avg"
    min = "min"
    max = "max"
    none = "none"


PRIMARY_COLOR = "rgb(237, 173, 8)"
SECONDARY_COLOR = "rgb(255, 242, 174)"
