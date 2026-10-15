"""백엔드 테스트 공용 fixture (계약·단위 공통). 슬라이스 세션은 수정하지 않는다.

- DB: docker compose 의 colorfit_test 데이터베이스. 테스트마다 전체 테이블 비움
- 외부 의존: Storage=memory, YouCam=mock, Embedding=fake (환경변수로 강제)
"""
import io
import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://colorfit:colorfit@localhost:5432/colorfit_test"
)
os.environ["STORAGE_MODE"] = "memory"
os.environ["YOUCAM_MODE"] = "mock"
os.environ["EMBEDDING_MODE"] = "fake"
os.environ["JWT_SECRET"] = "test-secret-key-for-pytest-only-0123456789"

from collections.abc import Callable, Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from common.entity import Base, Pin, Product, User  # noqa: E402
from common.enums import AgeGroup, Category, Gender, Style  # noqa: E402
from main import app  # noqa: E402
from shared.database import get_engine, get_session_factory  # noqa: E402
from shared.embedding import FakeEmbeddingModel, get_embedding_model  # noqa: E402
from shared.security import create_access_token, hash_password  # noqa: E402
from shared.storage import MemoryStorage, get_storage  # noqa: E402
from shared.youcam import MockYouCamClient, get_youcam_client  # noqa: E402


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:  # lifespan → initialize_database
        yield test_client


@pytest.fixture(autouse=True)
def clean_state(client: TestClient) -> Iterator[None]:
    yield
    table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with get_engine().begin() as connection:
        connection.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
    get_storage.cache_clear()
    get_youcam_client.cache_clear()


@pytest.fixture
def database_session() -> Iterator[Session]:
    session = get_session_factory()()
    yield session
    session.close()


@pytest.fixture
def storage() -> MemoryStorage:
    return get_storage()  # type: ignore[return-value]


@pytest.fixture
def youcam_client() -> MockYouCamClient:
    """속성으로 동작 변경: face_detected, skin_color_hex, cloth_fitting_succeeds"""
    return get_youcam_client()  # type: ignore[return-value]


@pytest.fixture
def embedding_model() -> FakeEmbeddingModel:
    return get_embedding_model()  # type: ignore[return-value]


@pytest.fixture
def create_user(database_session: Session) -> Callable[..., User]:
    """DB 에 직접 사용자 생성. create_user(nickname="a", age_group=..., gender=..., season=..., selfie_key=...)"""

    def factory(nickname: str = "tester", password: str = "password1234", **columns) -> User:
        user = User(nickname=nickname, password_hash=hash_password(password), **columns)
        database_session.add(user)
        database_session.commit()
        return user

    return factory


@pytest.fixture
def auth_headers() -> Callable[[User], dict[str, str]]:
    return lambda user: {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def create_product(database_session: Session, embedding_model: FakeEmbeddingModel) -> Callable[..., Product]:
    """DB 에 직접 상품 생성. 지정하지 않은 컬럼은 기본값."""
    counter = {"value": 0}

    def factory(**columns) -> Product:
        counter["value"] += 1
        number = counter["value"]
        defaults = dict(
            naver_product_id=f"naver-{number}",
            title=f"테스트 니트 {number}",
            price=39000,
            mall_name="테스트몰",
            purchase_url=f"https://shopping.test/products/{number}",
            image_url=f"https://image.test/products/{number}.jpg",
            gender=Gender.FEMALE,
            age_group=AgeGroup.TWENTIES,
            style=Style.MINIMAL,
            category=Category.TOP,
            color_lab=[70.0, 5.0, 20.0],
            embedding=embedding_model.embed_texts([f"product-{number}"])[0],
        )
        defaults.update(columns)
        product = Product(**defaults)
        database_session.add(product)
        database_session.commit()
        return product

    return factory


@pytest.fixture
def create_pin(database_session: Session, embedding_model: FakeEmbeddingModel) -> Callable[..., Pin]:
    """DB 에 직접 핀(스와이프용 코디 사진) 생성. 지정하지 않은 컬럼은 기본값."""
    counter = {"value": 0}

    def factory(**columns) -> Pin:
        counter["value"] += 1
        number = counter["value"]
        defaults = dict(
            image_url=f"https://image.test/pins/{number}.jpg",
            gender=Gender.FEMALE,
            age_group=AgeGroup.TWENTIES,
            style=Style.MINIMAL,
            embedding=embedding_model.embed_texts([f"pin-{number}"])[0],
        )
        defaults.update(columns)
        pin = Pin(**defaults)
        database_session.add(pin)
        database_session.commit()
        return pin

    return factory


@pytest.fixture
def sample_image_bytes() -> Callable[..., bytes]:
    """유효한 jpg/png 바이트 생성. sample_image_bytes(color=(200, 160, 130), image_format="JPEG")"""

    def factory(color: tuple[int, int, int] = (200, 160, 130), image_format: str = "JPEG", size: int = 512) -> bytes:
        buffer = io.BytesIO()
        Image.new("RGB", (size, size), color).save(buffer, format=image_format)
        return buffer.getvalue()

    return factory

