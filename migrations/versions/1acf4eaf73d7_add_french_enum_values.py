"""add_french_enum_values

Revision ID: 1acf4eaf73d7
Revises: 6d7735a07d38
Create Date: 2025-12-13 14:13:47.898892
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '1acf4eaf73d7'
down_revision = '6d7735a07d38'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # DocumentType values (assuming these are already uppercase in dev)
    op.execute("ALTER TYPE documenttype RENAME VALUE 'DEVIS' TO 'devis'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'FACTURE' TO 'facture'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'AVOIR' TO 'avoir'")

    # DocumentStatus values (rename English → French)
    op.execute("ALTER TYPE documentstatus RENAME VALUE 'DRAFT' TO 'brouillon'")
    op.execute("ALTER TYPE documentstatus RENAME VALUE 'SENT' TO 'en_attente'")
    op.execute("ALTER TYPE documentstatus RENAME VALUE 'PAID' TO 'paye'")
    op.execute("ALTER TYPE documentstatus RENAME VALUE 'OVERDUE' TO 'en_retard'")
    op.execute("ALTER TYPE documentstatus RENAME VALUE 'CANCELLED' TO 'annule'")

    # PaymentStatus values (assuming English in dev)
    op.execute("ALTER TYPE paymentstatus RENAME VALUE 'NON_PAYE' TO 'non_paye'")
    op.execute("ALTER TYPE paymentstatus RENAME VALUE 'PARTIEL' TO 'partiel'")
    op.execute("ALTER TYPE paymentstatus RENAME VALUE 'PAYE' TO 'paye'")
    op.execute("ALTER TYPE paymentstatus RENAME VALUE 'EN_RETARD' TO 'en_retard'")


def downgrade() -> None:
    # Revert French → English

    # DocumentType
    op.execute("ALTER TYPE documenttype RENAME VALUE 'devis' TO 'DEVIS'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'facture' TO 'FACTURE'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'avoir' TO 'AVOIR'")

    # DocumentStatus
    op.execute("ALTER TYPE documentstatus RENAME VALUE 'brouillon' TO 'DRAFT'")
    op.execute("ALTER TYPE documentstatus RENAME VALUE 'en_attente' TO 'SENT'")
    op.execute("ALTER TYPE documentstatus RENAME VALUE 'paye' TO 'PAID'")
    op.execute("ALTER TYPE documentstatus RENAME VALUE 'en_retard' TO 'OVERDUE'")
    op.execute("ALTER TYPE documentstatus RENAME VALUE 'annule' TO 'CANCELLED'")

    # PaymentStatus
    op.execute("ALTER TYPE paymentstatus RENAME VALUE 'non_paye' TO 'NON_PAYE'")
    op.execute("ALTER TYPE paymentstatus RENAME VALUE 'partiel' TO 'PARTIEL'")
    op.execute("ALTER TYPE paymentstatus RENAME VALUE 'paye' TO 'PAYE'")
    op.execute("ALTER TYPE paymentstatus RENAME VALUE 'en_retard' TO 'EN_RETARD'")
