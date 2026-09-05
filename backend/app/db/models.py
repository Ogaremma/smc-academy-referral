from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """Telegram User database model."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False
    )
    deleted_telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, index=True
    )
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    referral_code: Mapped[Optional["ReferralCode"]] = relationship(
        "ReferralCode", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    referrals: Mapped[List["Referral"]] = relationship(
        "Referral", back_populates="referrer", cascade="all, delete-orphan"
    )
    referral_attribution: Mapped[Optional["TelegramReferral"]] = relationship(
        "TelegramReferral",
        foreign_keys="TelegramReferral.referred_user_id",
        back_populates="referred_user",
        uselist=False,
    )
    referred_users: Mapped[List["TelegramReferral"]] = relationship(
        "TelegramReferral",
        foreign_keys="TelegramReferral.referrer_user_id",
        back_populates="referrer",
        overlaps="referral_code,telegram_referrals",
    )


class ReferralCode(Base):
    """User unique referral code model."""
    __tablename__ = "referral_codes"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_referral_codes_id_user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    code: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="referral_code")
    referrals: Mapped[List["Referral"]] = relationship(
        "Referral", back_populates="referral_code"
    )
    telegram_referrals: Mapped[List["TelegramReferral"]] = relationship(
        "TelegramReferral",
        back_populates="referral_code",
        overlaps="referred_users,referrer",
    )


class TelegramReferral(Base):
    """Immutable Telegram-native referrer attribution for a user."""
    __tablename__ = "telegram_referrals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["referral_code_id", "referrer_user_id"],
            ["referral_codes.id", "referral_codes.user_id"],
            name="fk_telegram_referrals_code_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "referred_user_id",
            name="uq_telegram_referrals_referred_user_id",
        ),
        CheckConstraint(
            "referrer_user_id <> referred_user_id",
            name="ck_telegram_referrals_no_self_referral",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    referrer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    referred_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    referral_code_id: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    referrer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[referrer_user_id],
        back_populates="referred_users",
        overlaps="referral_code,telegram_referrals",
    )
    referred_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[referred_user_id],
        back_populates="referral_attribution",
    )
    referral_code: Mapped["ReferralCode"] = relationship(
        "ReferralCode",
        back_populates="telegram_referrals",
        overlaps="referred_users,referrer",
    )


class Referral(Base):
    """
    Referral record created ONLY upon verified Google Form submission.
    """
    __tablename__ = "referrals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('verified', 'pending', 'rejected')",
            name="ck_referrals_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    referral_code_id: Mapped[int] = mapped_column(
        ForeignKey("referral_codes.id", ondelete="RESTRICT"), nullable=False
    )
    referrer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    google_form_response_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False
    )
    candidate_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    candidate_telegram_handle: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="verified", nullable=False
    )  # "verified", "rejected", "pending"

    registered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    referral_code: Mapped["ReferralCode"] = relationship(
        "ReferralCode", back_populates="referrals"
    )
    referrer: Mapped["User"] = relationship("User", back_populates="referrals")


class WebhookLog(Base):
    """Audit log for incoming Google Apps Script webhooks."""
    __tablename__ = "webhook_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    google_form_response_id: Mapped[Optional[str]] = mapped_column(
        String(128), index=True, nullable=True
    )
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
