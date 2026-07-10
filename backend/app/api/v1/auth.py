from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, is_admin_email
from app.core.config import settings
from app.core.email import render_template, send_email
from app.core.supabase_admin import get_admin_client

log = logging.getLogger(__name__)

router = APIRouter()


class SignupRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)


class MeResponse(BaseModel):
    email: str
    is_admin: bool


class SignupResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ForgotPasswordResponse(BaseModel):
    message: str


_FORGOT_PASSWORD_MESSAGE = "Jika email terdaftar, kami sudah mengirim link reset password."


@router.get("/me", response_model=MeResponse)
async def me(user: dict = Depends(get_current_user)) -> MeResponse:
    email = user.get("email") or ""
    return MeResponse(email=email, is_admin=is_admin_email(email))


@router.post("/signup", response_model=SignupResponse)
async def signup(body: SignupRequest) -> SignupResponse:
    sb = get_admin_client()

    try:
        create_res = sb.auth.admin.create_user({
            "email": body.email,
            "password": body.password,
            "email_confirm": False,
        })
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        link_res = sb.auth.admin.generate_link({
            "type": "signup",
            "email": body.email,
            "password": body.password,
            "options": {"redirect_to": f"{settings.APP_BASE_URL}/auth/callback"},
        })
        action_link = link_res.properties.action_link

        html = render_template("confirm_signup.html", action_link=action_link)
        send_email(body.email, "Konfirmasi akun Astalink kamu", html)
    except Exception as exc:
        log.error(
            "signup: created user %s but failed to send confirmation email (%s) — "
            "deleting the orphaned account so the user can retry signup",
            body.email, exc,
        )
        sb.auth.admin.delete_user(create_res.user.id)
        raise HTTPException(
            status_code=500,
            detail="Gagal mengirim email konfirmasi. Silakan coba daftar lagi.",
        )

    return SignupResponse(message="Cek email kamu untuk konfirmasi akun.")


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(body: ForgotPasswordRequest) -> ForgotPasswordResponse:
    sb = get_admin_client()

    try:
        link_res = sb.auth.admin.generate_link({
            "type": "recovery",
            "email": body.email,
            "options": {
                "redirect_to": f"{settings.APP_BASE_URL}/auth/callback?next=/reset-password",
            },
        })
        action_link = link_res.properties.action_link
        html = render_template("reset_password.html", action_link=action_link)
        send_email(body.email, "Reset password Astalink kamu", html)
    except Exception as exc:
        # Deliberately swallowed — the response must be identical whether
        # or not the email is registered (see test_forgot_password_message_
        # identical_regardless_of_email_existence).
        log.warning("forgot_password: could not send reset email to %s: %s", body.email, exc)

    return ForgotPasswordResponse(message=_FORGOT_PASSWORD_MESSAGE)
