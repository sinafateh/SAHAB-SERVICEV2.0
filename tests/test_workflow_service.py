import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    Attachment,
    Base,
    Customer,
    Notification,
    OrderStatus,
    Panel,
    RepairOrder,
    CaseTimelineEvent,
    TechnicalStageTiming,
    User,
    WorkflowTransition,
)
from app.services.workflow_service import WorkflowService


class WorkflowServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

        self.reception = User(
            username="reception",
            password_hash="x",
            full_name="پذیرش",
            role="RECEPTION",
            department="RECEPTION",
            is_active=True,
        )
        self.tech_one = User(
            username="tech-one",
            password_hash="x",
            full_name="تکنسین یک",
            role="TECHNICAL",
            department="TECHNICAL",
            is_active=True,
        )
        self.tech_two = User(
            username="tech-two",
            password_hash="x",
            full_name="تکنسین دو",
            role="TECHNICAL",
            department="TECHNICAL",
            is_active=True,
        )
        self.session.add_all([self.reception, self.tech_one, self.tech_two])
        self.session.flush()

        customer = Customer(name="مشتری تست", phone="09120000000")
        panel = Panel(
            brand="Brand",
            model="Model",
            serial_number="SN-TEST",
            part_number="PN-TEST",
        )
        self.session.add_all([customer, panel])
        self.session.flush()
        self.order = RepairOrder(
            tracking_code="SR-TEST",
            status=OrderStatus.REGISTERED,
            current_stage="RECEPTION_INTAKE",
            current_user_id=self.reception.id,
            customer_id=customer.id,
            panel_id=panel.id,
        )
        self.session.add(self.order)
        self.session.commit()
        self.session.refresh(self.order)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_handoff_rejection_reassignment_and_receive(self):
        transition = WorkflowService.transfer_order(
            self.session,
            self.order,
            self.reception,
            self.tech_one.id,
            "TECHNICAL_DIAGNOSIS",
            "TECHNICAL",
        )
        self.assertEqual(transition.status, "PENDING")
        self.assertEqual(len(WorkflowService.get_my_tasks(self.session, self.tech_one.id)), 1)

        transition = WorkflowService.change_recipient(
            self.session,
            transition.id,
            self.reception,
            self.tech_two.id,
            "TECHNICAL",
        )
        transition = WorkflowService.reject_transition(
            self.session,
            transition.id,
            self.tech_two,
            "در دسترس نیستم",
        )
        self.assertEqual(transition.status, "REJECTED")

        transition = WorkflowService.transfer_order(
            self.session,
            self.order,
            self.reception,
            self.tech_one.id,
            "TECHNICAL_DIAGNOSIS",
            "TECHNICAL",
        )
        WorkflowService.receive_transition(self.session, transition.id, self.tech_one)
        self.session.refresh(self.order)

        self.assertEqual(self.order.current_stage, "TECHNICAL_DIAGNOSIS")
        self.assertEqual(self.order.current_user_id, self.tech_one.id)
        self.assertEqual(self.session.query(WorkflowTransition).count(), 2)
        self.assertGreaterEqual(self.session.query(Notification).count(), 3)

    def test_technical_stage_timing_creates_duration_and_timeline_events(self):
        transition = WorkflowService.transfer_order(
            self.session,
            self.order,
            self.reception,
            self.tech_one.id,
            "TECHNICAL_DIAGNOSIS",
            "TECHNICAL",
        )
        WorkflowService.receive_transition(self.session, transition.id, self.tech_one)
        self.session.refresh(self.order)

        started = WorkflowService.start_timing(
            self.session, self.order, self.tech_one, "TECHNICAL_DIAGNOSIS"
        )
        started_status = started.status
        completed = WorkflowService.complete_timing(
            self.session, self.order, self.tech_one, "TECHNICAL_DIAGNOSIS"
        )

        self.assertEqual(started_status, "RUNNING")
        self.assertEqual(completed.status, "COMPLETED")
        self.assertIsNotNone(completed.completed_at)
        self.assertGreaterEqual(completed.duration_seconds, 0)
        self.assertEqual(self.session.query(TechnicalStageTiming).count(), 1)
        self.assertEqual(self.session.query(CaseTimelineEvent).count(), 4)

    def test_technical_repair_must_return_to_diagnosing_technician_and_final_test_must_be_different(self):
        management = User(
            username="management",
            password_hash="x",
            full_name="مدیریت",
            role="MANAGEMENT",
            department="MANAGEMENT",
            is_active=True,
        )
        self.session.add(management)
        self.session.flush()

        diagnosis_transfer = WorkflowService.transfer_order(
            self.session,
            self.order,
            self.reception,
            self.tech_one.id,
            "TECHNICAL_DIAGNOSIS",
            "TECHNICAL",
        )
        WorkflowService.receive_transition(self.session, diagnosis_transfer.id, self.tech_one)
        WorkflowService.apply_action(
            self.session,
            self.order,
            self.tech_one,
            "DIAGNOSIS",
            "عیب‌یابی انجام شد",
        )
        self.session.refresh(self.order)

        management_transfer = WorkflowService.transfer_order(
            self.session,
            self.order,
            self.tech_one,
            management.id,
            "MANAGEMENT_PRICING",
            "MANAGEMENT",
        )
        WorkflowService.receive_transition(self.session, management_transfer.id, management)

        with self.assertRaises(Exception):
            WorkflowService.transfer_order(
                self.session,
                self.order,
                management,
                self.tech_two.id,
                "TECHNICAL_REPAIR",
                "TECHNICAL",
            )

        repair_transfer = WorkflowService.transfer_order(
            self.session,
            self.order,
            management,
            self.tech_one.id,
            "TECHNICAL_REPAIR",
            "TECHNICAL",
        )
        WorkflowService.receive_transition(self.session, repair_transfer.id, self.tech_one)
        WorkflowService.apply_action(
            self.session,
            self.order,
            self.tech_one,
            "REPAIR_COMPLETE",
            "تعمیر انجام شد",
        )
        self.session.refresh(self.order)

        with self.assertRaises(Exception):
            WorkflowService.transfer_order(
                self.session,
                self.order,
                self.tech_one,
                self.tech_one.id,
                "TECHNICAL_FINAL_TEST",
                "TECHNICAL",
            )

        final_test_transfer = WorkflowService.transfer_order(
            self.session,
            self.order,
            self.tech_one,
            self.tech_two.id,
            "TECHNICAL_FINAL_TEST",
            "TECHNICAL",
        )
        self.assertEqual(final_test_transfer.to_user_id, self.tech_two.id)

    def test_delivery_requires_receipt_and_closed_case_is_locked(self):
        self.order.current_stage = "RECEPTION_DELIVERY"
        self.order.status = OrderStatus.READY_DELIVERY
        self.order.current_user_id = self.reception.id
        self.session.commit()

        with self.assertRaises(Exception):
            WorkflowService.apply_action(self.session, self.order, self.reception, "DELIVER")

        self.session.add(
            Attachment(
                file_name="delivery-receipt.pdf",
                file_path="/uploads/attachments/1/delivery-receipt.pdf",
                file_type="pdf",
                stage="DELIVERY",
                is_delivery_receipt=True,
                repair_order_id=self.order.id,
                uploaded_by=self.reception.id,
            )
        )
        self.session.commit()
        WorkflowService.apply_action(self.session, self.order, self.reception, "DELIVER")
        self.session.refresh(self.order)
        self.assertEqual(self.order.current_stage, "COMPLETED")
        self.assertEqual(self.order.status, OrderStatus.DELIVERED)

        with self.assertRaises(Exception):
            WorkflowService.start_timing(
                self.session,
                self.order,
                self.reception,
                "TECHNICAL_DIAGNOSIS",
            )


if __name__ == "__main__":
    unittest.main()
