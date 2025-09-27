from dataclasses import dataclass


@dataclass
class CallbackUrl:
    callback_host: str = "localhost"
    callback_port: int = 8080
    callback_route: str = "/callback"

    def url(self) -> str:
        """Construct the full callback URL.

        Returns:
            The complete callback URL.
        """
        return f"http://{self.callback_host}:{self.callback_port}{self.callback_route}"
