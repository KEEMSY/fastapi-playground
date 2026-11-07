import os

from celery import Celery

celery_app = Celery(
    "order_flow",
    broker=os.getenv("CELERY_BROKER_URL", "amqp://order_flow:order_flow@localhost:5673//"),
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="order.tasks",
    worker_prefetch_multiplier=1,
    task_serializer="json",
    accept_content=["json"],
    broker_transport_options={"confirm_publish": True},
)
celery_app.autodiscover_tasks(["order_flow"])
