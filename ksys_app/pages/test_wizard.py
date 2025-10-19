"""Test wizard page - minimal version"""
import reflex as rx


class TestWizardState(rx.State):
    step: int = 1

    def next_step(self):
        if self.step < 3:
            self.step += 1

    def prev_step(self):
        if self.step > 1:
            self.step -= 1


@rx.page("/test/wizard")
def test_wizard():
    return rx.box(
        rx.vstack(
            rx.heading(f"Test Wizard - Step {TestWizardState.step}", size="6"),

            rx.cond(
                TestWizardState.step == 1,
                rx.text("Step 1: Select something", size="4"),
                rx.cond(
                    TestWizardState.step == 2,
                    rx.text("Step 2: Configure something", size="4"),
                    rx.text("Step 3: Results", size="4"),
                ),
            ),

            rx.hstack(
                rx.button("Previous", on_click=TestWizardState.prev_step),
                rx.button("Next", on_click=TestWizardState.next_step),
                spacing="3",
            ),

            spacing="4",
        ),
        padding="8",
    )
