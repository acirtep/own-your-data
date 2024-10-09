from enum import Enum


class ExtendedEnum(Enum):

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class SupportedPlots(str, ExtendedEnum):
    bar = "bar"
    line = "line"
    sankey = "sankey"
    heatmap = "heatmap"
    scatter = "scatter"


class SupportedAggregationMethods(str, ExtendedEnum):
    count = "count"
    sum = "sum"
    avg = "avg"
    min = "min"
    max = "max"
