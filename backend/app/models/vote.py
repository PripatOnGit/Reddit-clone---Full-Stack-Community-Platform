from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        CheckConstraint(
            "(post_id IS NOT NULL AND comment_id IS NULL) OR (post_id IS NULL AND comment_id IS NOT NULL)",
            name="ck_votes_exactly_one_target",
        ),
        CheckConstraint("value IN (-1, 1)", name="ck_votes_value_range"),
        Index("ux_votes_user_post", "user_id", "post_id", unique=True, postgresql_where="post_id IS NOT NULL"),
        Index(
            "ux_votes_user_comment", "user_id", "comment_id", unique=True, postgresql_where="comment_id IS NOT NULL"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    comment_id: Mapped[int | None] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)
    value: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    user: Mapped["User"] = relationship(back_populates="votes")
    post: Mapped["Post | None"] = relationship(back_populates="votes")
    comment: Mapped["Comment | None"] = relationship(back_populates="votes")
