"""Settings controller — LLM endpoint configuration."""

from dataclasses import dataclass
from typing import Annotated

import structlog
from litestar import Controller, Request, get, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Template

from easyorario.exceptions import LLMConfigError
from easyorario.guards.auth import requires_responsible_professor
from easyorario.i18n.errors import MESSAGES
from easyorario.services.llm import LLMService, get_llm_config, set_llm_config

_log = structlog.get_logger()


@dataclass
class LLMConfigFormData:
    base_url: str = ""
    api_key: str = ""
    model_id: str = ""


class SettingsController(Controller):
    """LLM endpoint configuration for Responsible Professors."""

    path = "/impostazioni"

    @get("/", guards=[requires_responsible_professor])
    async def show_settings(self, request: Request) -> Template:
        """Render the LLM configuration form."""
        llm_config = get_llm_config(request.session)
        return Template(
            template_name="pages/settings.html",
            context={
                "user": request.user,
                "base_url": llm_config["base_url"] if llm_config else "",
                "model_id": llm_config["model_id"] if llm_config else "",
                "has_config": llm_config is not None,
            },
        )

    @post("/", guards=[requires_responsible_professor])
    async def save_settings(
        self,
        request: Request,
        data: Annotated[LLMConfigFormData, Body(media_type=RequestEncodingType.URL_ENCODED)],
        llm_service: LLMService,
    ) -> Template:
        """Process LLM configuration form submission."""
        base_url = data.base_url.strip()
        api_key = data.api_key.strip()
        model_id = data.model_id.strip()

        ctx = {"user": request.user, "base_url": base_url, "model_id": model_id}

        if not base_url:
            return Template(
                "pages/settings.html",
                context={
                    **ctx,
                    "error": MESSAGES["llm_base_url_required"],
                    "has_config": get_llm_config(request.session) is not None,
                },
            )

        if not api_key:
            existing = get_llm_config(request.session)
            if existing:
                api_key = existing["api_key"]
            else:
                return Template(
                    "pages/settings.html",
                    context={**ctx, "error": MESSAGES["llm_api_key_required"], "has_config": False},
                )

        try:
            await llm_service.test_connectivity(base_url, api_key, model_id)
        except LLMConfigError as exc:
            return Template(
                "pages/settings.html",
                context={
                    **ctx,
                    "error": MESSAGES[exc.error_key],
                    "has_config": get_llm_config(request.session) is not None,
                },
            )

        set_llm_config(request, base_url, api_key, model_id)
        await _log.ainfo("llm_config_saved", base_url=base_url)

        return Template(
            "pages/settings.html",
            context={**ctx, "success": MESSAGES["llm_config_saved"], "has_config": True},
        )
