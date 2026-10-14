"""make tasks.done not null with server default

Revision ID: fde23c7ca11a
Revises: fd9a1b6bb150
Create Date: 2026-10-13 21:21:53.726119

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fde23c7ca11a'
down_revision: Union[str, Sequence[str], None] = 'fd9a1b6bb150'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 步驟 1：先把現有的空值補成 false，否則下一步會被拒絕
    op.execute("UPDATE tasks SET done = false WHERE done IS NULL")
    # 步驟 2：設定資料庫端的預設值 false，之後新資料不會再是空值
    op.alter_column('tasks', 'done', existing_type=sa.BOOLEAN(), server_default=sa.false())
    # 步驟 3：最後才收緊成不准空值
    op.alter_column('tasks', 'done', existing_type=sa.BOOLEAN(), nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 降級順序與升級相反：先放寬成可以為空
    op.alter_column('tasks', 'done', existing_type=sa.BOOLEAN(), nullable=True)
    # 再拿掉資料庫端的預設值
    op.alter_column('tasks', 'done', existing_type=sa.BOOLEAN(), server_default=None)
    # 注意：升級時補成 false 的資料不會還原，因為已無法知道原本哪幾筆是空值
