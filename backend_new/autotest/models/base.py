import typing

from sqlalchemy import Column, Boolean, DateTime, Integer, func, select, update, delete, insert, Select, \
    Executable, Result, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import as_declarative

from autotest.corelibs import g
from autotest.corelibs.pagination import parse_pagination
from autotest.db.session import provide_session
from autotest.exceptions import AccessTokenFail
from autotest.utils.current_user import current_user
from autotest.utils.serialize import unwrap_scalars


@as_declarative()
class Base:
    """ 基本表 """

    # db.scalar(sql) 返回的是标量(原始数据) <models.department.Department object at 0x000002F2C2D22110>
    # db.execute(sql) 返回的是元组 (<models.department.Department object at 0x000002F2C2D22110>)
    # db.scalars(sql).all()  [<models...>, <models...>, <models...>]
    # db.execute(sql).fetchall()  [(<models...>,), (<models...>,), (<models...>,)]

    __name__: str  # 表名
    __table_args__ = {"mysql_charset": "utf8"}  # 设置表的字符集

    __mapper_args__ = {"eager_defaults": True}  # 防止 insert 插入后不刷新

    # @declared_attr
    # def __tablename__(cls) -> str:
    #     """将类名小写并转化为表名 __tablename__"""
    #     return cls.__name__.lower()

    id = Column(Integer(), nullable=False, primary_key=True, autoincrement=True)
    creation_date = Column(DateTime(), default=func.now(), comment='创建时间')
    created_by = Column(Integer, nullable=True, comment='创建人ID')
    updation_date = Column(DateTime(), default=func.now(), onupdate=func.now(), nullable=False, comment='更新时间')
    updated_by = Column(Integer, nullable=True, comment='更新人ID')
    enabled_flag = Column(Boolean(), default=1, nullable=False, comment='是否删除, 0 删除 1 非删除')
    trace_id = Column(String(255), nullable=False, comment="trace_id")

    @classmethod
    async def get(cls, id: typing.Union[int, str], to_dict=False) -> typing.Union["Base", typing.Any]:
        """
        :param id: 查询id
        :param to_dict: 转字典
        :return: 模型对象 <models...>
        """
        sql = select(cls).where(cls.id == id, cls.enabled_flag == 1)
        result = await cls.execute(sql)
        data = result.scalar()
        return data if not to_dict else unwrap_scalars(data)

    @classmethod
    async def get_all(cls) -> typing.Optional[typing.Any]:
        """
        :return: 返回所有数据  list[dict]
        """
        stmt = select(cls.get_table_columns()).where(cls.enabled_flag == 1)
        return await cls.get_result(stmt)

    @classmethod
    async def create_or_update(cls,
                               params: typing.Union[typing.Dict],
                               is_async=False) -> typing.Dict[typing.Text, typing.Any]:
        """
        :param params: 更新数据 dict
        :param is_async: 是否异步
        :return: 更新后的数据 dict
        """
        if not isinstance(params, dict):
            raise ValueError("更新参数错误！")
        params = {key: value for key, value in params.items() if hasattr(cls, key)}
        id = params.get("id", None)
        if g.trace_id:
            params['trace_id'] = g.trace_id
        if not is_async:
            try:
                current_user_info = await current_user(g.token)
            except AccessTokenFail as err:
                current_user_info = None
            if current_user_info:
                current_user_id = current_user_info.get("id", None)
                params["updated_by"] = current_user_id
                if not id:
                    params["created_by"] = current_user_id
        if id:
            stmt = update(cls).where(cls.id == id).values(**params)
        else:
            stmt = insert(cls).values(**params)
        result = await cls.execute(stmt)
        if result.is_insert:
            (primary_key,) = result.inserted_primary_key
            params["id"] = primary_key
        return params

    @classmethod
    async def create(cls, params: typing.Dict, to_dict: bool = False) -> typing.Union["Base", typing.Dict]:
        """
        插入数据
        :param params: 批量插入数据
        :param to_dict: 是否转字典
        :return: 插入数量
        """
        if not isinstance(params, dict):
            raise ValueError("参数错误")
        params = {key: value for key, value in params.items() if hasattr(cls, key)}
        if g.trace_id:
            params['trace_id'] = g.trace_id
        stmt = insert(cls).values(**params)
        result = await cls.execute(stmt)
        (primary_key,) = result.inserted_primary_key
        params["id"] = primary_key
        return cls(**params) if not to_dict else params

    @classmethod
    async def batch_create(cls, params: typing.List) -> int:
        """
        批量插入数据
        :param params: 批量插入数据
        :return: 插入数量
        """
        if not isinstance(params, list):
            raise ValueError("参数错误，参数必须为列表")
        params = await cls.handle_params(params)
        stmt = insert(cls).values(params)
        result = await cls.execute(stmt)
        return result.rowcount

    @classmethod
    async def handle_params(cls, params: typing.List) -> typing.List:
        """
        :param params: 参数列表
        :return: 过滤好的参数
        """
        if isinstance(params, dict):
            params = {key: value for key, value in params.items() if hasattr(cls, key)}
            try:
                current_user_info = await current_user(g.token)
            except AccessTokenFail as err:
                current_user_info = None
            if current_user_info:
                current_user_id = current_user_info.get("id", None)
                params["updated_by"] = current_user_id
                params["created_by"] = current_user_id
        elif isinstance(params, list):
            params = [await cls.handle_params(p) for p in params]
        return params

    @classmethod
    async def delete(cls, id: typing.Union[int, str], _hard: bool = False) -> int:
        """
        :param id: 删除数据id
        :param _hard:  False 逻辑删除， Ture 物理删除
        :return: sql影响行数
        """
        if _hard is False:
            stmt = update(cls).where(cls.id == id, cls.enabled_flag == 1).values(enabled_flag=0)
        else:
            stmt = delete(cls).where(cls.id == id)
        result = await cls.execute(stmt)
        return result.rowcount

    @classmethod
    @provide_session
    async def execute(cls, stmt: Executable, params: typing.Any = None, session: AsyncSession = None) -> Result[
        typing.Any]:
        """
        执行sql
        :param stmt: sqlalchemy Executable 对象
        :param params: params 参数
        :param session: session db会话链接
        :return:
        """
        return await session.execute(stmt, params)

    @classmethod
    async def pagination(cls, stmt: Select) -> typing.Dict[str, typing.Any]:
        """
        分页查询
        :param stmt: select对象
        :return:
        """
        return await parse_pagination(stmt)

    @classmethod
    def get_table_columns(cls) -> list:
        """
        获取模型所有字段
        :return:
        """
        return cls.__table__.columns

    @classmethod
    async def get_result(cls, stmt: Select, first=False) -> typing.Any:
        """
        <models...> or  <Row...>
        获取查询结果转转为dict

        first=True：
        {
            "key": "value"
            ...
        }
        first=False：
        [
            {
                "key1": "value1"
                ...
            },
            {
                "key2": "value2"
                ...
            }
        ]

        :param stmt: sqlalchemy Executable 对象
        :param first: 是否只取一条
        :return:
        """
        result = await cls.execute(stmt)
        data = result.first() if first else result.fetchall()
        return unwrap_scalars(data) if data else None