"""
Model Configuration State

Manages model hyperparameter configuration UI dynamically
without hardcoding parameter values.

Features:
- Load model schemas from ModelConfigService
- Dynamic form generation based on schema
- Validation before save
- CRUD operations on model_registry
"""

import reflex as rx
from typing import Dict, List, Any, Optional
from reflex.utils import console

from ..services.model_config_service import ModelConfigService
from ..db_orm import get_async_session


class ModelConfigState(rx.State):
    """State for managing model configurations"""

    # Model selection
    available_model_types: list[str] = ["auto_arima", "prophet", "xgboost", "ensemble"]
    selected_model_type: str = "auto_arima"
    selected_tag: str = "INLET_PRESSURE"

    # Schema and config
    model_schema: dict = {}
    current_config: dict = {}
    default_config: dict = {}

    # Saved models
    saved_models: list[dict] = []
    selected_model_id: Optional[int] = None

    # UI state
    is_loading: bool = False
    is_saving: bool = False
    error_message: str = ""
    success_message: str = ""
    validation_errors: list[str] = []

    @rx.event(background=True)
    async def load_schema(self):
        """Load schema for selected model type"""
        async with self:
            self.is_loading = True
            self.error_message = ""
            yield

        try:
            async with get_async_session() as session:
                service = ModelConfigService(session)

                # Get schema and default config
                schema = await service.get_model_schema(self.selected_model_type)
                default = await service.get_default_config(self.selected_model_type)

                async with self:
                    self.model_schema = schema
                    self.default_config = default
                    self.current_config = default.copy()
                    self.is_loading = False
                    yield

        except Exception as e:
            console.error(f"Failed to load schema: {e}")
            async with self:
                self.error_message = f"Failed to load schema: {e}"
                self.is_loading = False
                yield

    @rx.event(background=True)
    async def load_saved_models(self):
        """Load all saved model configurations for selected tag"""
        async with self:
            self.is_loading = True
            yield

        try:
            async with get_async_session() as session:
                service = ModelConfigService(session)

                models = await service.list_model_configs(
                    tag_name=self.selected_tag,
                    is_active=True
                )

                async with self:
                    self.saved_models = models
                    self.is_loading = False
                    yield

        except Exception as e:
            console.error(f"Failed to load models: {e}")
            async with self:
                self.error_message = f"Failed to load models: {e}"
                self.is_loading = False
                yield

    async def set_selected_model_type(self, model_type: str):
        """Change selected model type and load its schema"""
        self.selected_model_type = model_type
        return self.load_schema()

    async def set_selected_tag(self, tag: str):
        """Change selected tag and reload models"""
        self.selected_tag = tag
        return self.load_saved_models()

    async def update_param(self, param: str, value: Any):
        """Update a single parameter value"""
        self.current_config[param] = value
        self.validation_errors = []  # Clear errors on change

    async def reset_to_default(self):
        """Reset current config to defaults"""
        self.current_config = self.default_config.copy()
        self.validation_errors = []

    async def load_model_config(self, model_id: int):
        """Load configuration from saved model"""
        return self.load_model_config_bg(model_id)

    @rx.event(background=True)
    async def load_model_config_bg(self, model_id: int):
        """Background: Load configuration from saved model"""
        async with self:
            self.is_loading = True
            yield

        try:
            async with get_async_session() as session:
                service = ModelConfigService(session)

                config = await service.get_model_config(model_id)

                if config:
                    async with self:
                        self.current_config = config
                        self.selected_model_id = model_id
                        self.is_loading = False
                        self.success_message = f"Loaded model {model_id} configuration"
                        yield
                else:
                    async with self:
                        self.error_message = f"Model {model_id} has no configuration"
                        self.is_loading = False
                        yield

        except Exception as e:
            console.error(f"Failed to load model config: {e}")
            async with self:
                self.error_message = f"Failed to load config: {e}"
                self.is_loading = False
                yield

    @rx.event(background=True)
    async def save_config(self):
        """Validate and save current configuration"""
        async with self:
            self.is_saving = True
            self.error_message = ""
            self.success_message = ""
            self.validation_errors = []
            yield

        try:
            async with get_async_session() as session:
                service = ModelConfigService(session)

                # Validate
                is_valid, errors = await service.validate_config(
                    self.selected_model_type,
                    self.current_config
                )

                if not is_valid:
                    async with self:
                        self.validation_errors = errors
                        self.error_message = "Configuration validation failed"
                        self.is_saving = False
                        yield
                    return

                # Save (update existing or create new)
                if self.selected_model_id:
                    # Update existing
                    success = await service.save_model_config(
                        model_id=self.selected_model_id,
                        hyperparameters=self.current_config
                    )
                    message = f"Updated model {self.selected_model_id}"
                else:
                    # Create new
                    model_id = await service.create_model_config(
                        tag_name=self.selected_tag,
                        model_type=self.selected_model_type,
                        version="custom_" + rx.State.router.session.client_token[:8],
                        hyperparameters=self.current_config
                    )
                    message = f"Created new model {model_id}"

                # Reload saved models
                models = await service.list_model_configs(
                    tag_name=self.selected_tag,
                    is_active=True
                )

                async with self:
                    self.saved_models = models
                    self.success_message = message
                    self.is_saving = False
                    yield

        except Exception as e:
            console.error(f"Failed to save config: {e}")
            async with self:
                self.error_message = f"Failed to save: {e}"
                self.is_saving = False
                yield

    @rx.event(background=True)
    async def delete_model(self, model_id: int):
        """Delete a saved model configuration"""
        try:
            async with get_async_session() as session:
                service = ModelConfigService(session)

                success = await service.delete_model_config(
                    model_id=model_id,
                    soft_delete=True
                )

                if success:
                    # Reload models
                    models = await service.list_model_configs(
                        tag_name=self.selected_tag,
                        is_active=True
                    )

                    async with self:
                        self.saved_models = models
                        self.success_message = f"Deleted model {model_id}"
                        yield
                else:
                    async with self:
                        self.error_message = f"Failed to delete model {model_id}"
                        yield

        except Exception as e:
            console.error(f"Failed to delete model: {e}")
            async with self:
                self.error_message = f"Failed to delete: {e}"
                yield

    @rx.event(background=True)
    async def clone_model(self, source_model_id: int):
        """Clone an existing model configuration"""
        try:
            async with get_async_session() as session:
                service = ModelConfigService(session)

                new_model_id = await service.clone_model_config(
                    source_model_id=source_model_id,
                    new_version=f"clone_{rx.State.router.session.client_token[:8]}"
                )

                # Reload models
                models = await service.list_model_configs(
                    tag_name=self.selected_tag,
                    is_active=True
                )

                async with self:
                    self.saved_models = models
                    self.success_message = f"Cloned model {source_model_id} → {new_model_id}"
                    yield

        except Exception as e:
            console.error(f"Failed to clone model: {e}")
            async with self:
                self.error_message = f"Failed to clone: {e}"
                yield


# Dynamic form component generator (no hardcoding!)
def render_param_input(param: str, info: dict) -> rx.Component:
    """Render appropriate input for parameter based on schema"""
    param_type = info.get("type", "text")
    description = info.get("description", "")
    default = info.get("default")

    if param_type == "boolean":
        return rx.vstack(
            rx.hstack(
                rx.switch(
                    checked=ModelConfigState.current_config.get(param, default),
                    on_change=lambda v: ModelConfigState.update_param(param, v),
                ),
                rx.text(param, weight="bold"),
                spacing="2",
            ),
            rx.text(description, size="1", color="gray"),
            spacing="1",
            align="start",
        )

    elif param_type == "integer":
        return rx.vstack(
            rx.text(param, weight="bold"),
            rx.number_input(
                value=ModelConfigState.current_config.get(param, default),
                on_change=lambda v: ModelConfigState.update_param(param, int(v)),
                min_=info.get("min"),
                max_=info.get("max"),
            ),
            rx.text(description, size="1", color="gray"),
            spacing="1",
            align="start",
        )

    elif param_type == "float":
        return rx.vstack(
            rx.text(param, weight="bold"),
            rx.number_input(
                value=ModelConfigState.current_config.get(param, default),
                on_change=lambda v: ModelConfigState.update_param(param, float(v)),
                min_=info.get("min"),
                max_=info.get("max"),
                step=0.01,
            ),
            rx.text(description, size="1", color="gray"),
            spacing="1",
            align="start",
        )

    elif param_type == "select":
        return rx.vstack(
            rx.text(param, weight="bold"),
            rx.select(
                info.get("options", []),
                value=ModelConfigState.current_config.get(param, default),
                on_change=lambda v: ModelConfigState.update_param(param, v),
            ),
            rx.text(description, size="1", color="gray"),
            spacing="1",
            align="start",
        )

    else:  # text
        return rx.vstack(
            rx.text(param, weight="bold"),
            rx.input(
                value=ModelConfigState.current_config.get(param, default),
                on_change=lambda v: ModelConfigState.update_param(param, v),
            ),
            rx.text(description, size="1", color="gray"),
            spacing="1",
            align="start",
        )
