from typing import Literal

from pydantic import BaseModel, Field, SecretStr


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    repository: str = ""
    site_url: str = ""


HostProtocol = Literal[
    "auto",
    "ssh/sftp",
    "ftp",
    "ftps",
    "cpanel",
    "plesk",
    "directadmin",
    "https/api",
]


class HostDetectRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=253)
    username: str = Field(default="", max_length=160)
    password: SecretStr | None = None
    protocol: HostProtocol = "auto"
    port: int | None = Field(default=None, ge=1, le=65535)


class HostConnectionTestRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=253)
    username: str = Field(min_length=1, max_length=160)
    password: SecretStr
    protocol: HostProtocol = "auto"
    port: int | None = Field(default=None, ge=1, le=65535)


class CommandRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class TaskApproval(BaseModel):
    confirmation: str = Field(min_length=1, max_length=100)
