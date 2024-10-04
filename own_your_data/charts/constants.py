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


class SupportedAggregationMethods(str, ExtendedEnum):
    count = "count"
    sum = "sum"
    # TODO has to take into account missing data
    # avg = "avg"
    # min = "min"
    # max = "max"
