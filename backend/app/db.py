from sqlmodel import SQLModel, create_engine, Session

DB_URL = "sqlite:///./conf_os.db"
engine = create_engine(DB_URL, echo=False)  # 디버깅 시 True로

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
