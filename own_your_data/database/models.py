from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import Sequence
from sqlalchemy import String
from sqlalchemy import text
from sqlalchemy.orm import as_declarative


@as_declarative()
class Base:
    pass


class AuditBaseMixin:
    date_created = Column(DateTime(timezone=True), server_default=text("current_timestamp"), nullable=False)
    date_updated = Column(DateTime(timezone=True), server_default=text("current_timestamp"), nullable=False)


category_unit_type_id_seq = Sequence("category_unit_type_id_seq")


class CategoryUnitTypes(Base, AuditBaseMixin):
    __tablename__ = "category_unit_types"

    category_unit_type_id = Column(
        Integer, category_unit_type_id_seq, server_default=category_unit_type_id_seq.next_value(), primary_key=True
    )
    category_unit = Column(String(10), nullable=False, unique=True)
