"""SQLAlchemy models for QuantLab user accounts."""

from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime
import numpy as np

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Platform user account."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    holdings = db.relationship(
        "PortfolioHolding",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="PortfolioHolding.ticker",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"


class PortfolioHolding(db.Model):
    """Holding in a user's portfolio."""

    __tablename__ = "portfolio_holdings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    ticker = db.Column(db.String(20), nullable=False)
    shares = db.Column(db.Float, nullable=False, default=1.0)
    buy_price = db.Column(db.Float, nullable=True)  # Cost basis per share in USD
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "ticker", name="uq_user_ticker"),
    )

    def to_dict(self, current_price: float | None = None) -> dict:
        cur = current_price if (current_price is not None and np.isfinite(current_price)) else self.buy_price
        val = (cur * self.shares) if (cur is not None) else 0.0
        cost = (self.buy_price * self.shares) if (self.buy_price is not None) else val
        pnl = (val - cost) if (cost > 0) else 0.0
        pnl_pct = (pnl / cost * 100.0) if (cost > 0) else 0.0
        return {
            "id": self.id,
            "ticker": self.ticker,
            "shares": round(float(self.shares), 4),
            "buyPrice": round(float(self.buy_price), 2) if self.buy_price is not None else None,
            "currentPrice": round(float(cur), 2) if cur is not None else None,
            "currentValue": round(float(val), 2),
            "costBasis": round(float(cost), 2),
            "pnl": round(float(pnl), 2),
            "pnlPct": round(float(pnl_pct), 2),
        }

    def __repr__(self) -> str:
        return f"<PortfolioHolding user_id={self.user_id} {self.ticker}: {self.shares} shares>"
