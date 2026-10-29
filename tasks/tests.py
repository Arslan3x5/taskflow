import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthTests(TestCase):
    def test_board_requires_login(self):
        response = self.client.get(reverse("board"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser",
            "password1": "S3cure-pass-123",
            "password2": "S3cure-pass-123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertEqual(self.client.get(reverse("board")).status_code, 200)


class TaskApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("arslan", password="pass12345")
        self.client.login(username="arslan", password="pass12345")

    def post(self, **data):
        return self.client.post(reverse("task_list"), json.dumps(data), content_type="application/json")

    def patch(self, task_id, **data):
        return self.client.patch(reverse("task_detail", args=[task_id]),
                                 json.dumps(data), content_type="application/json")

    def test_api_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("task_list")).status_code, 302)

    def test_create_and_list(self):
        self.assertEqual(self.post(title="Ship v1").status_code, 201)
        tasks = self.client.get(reverse("task_list")).json()["tasks"]
        self.assertEqual(tasks[0]["title"], "Ship v1")

    def test_rejects_empty_title(self):
        self.assertEqual(self.post(title="  ").status_code, 400)

    def test_rejects_invalid_priority(self):
        self.assertEqual(self.post(title="Bad", priority="urgent").status_code, 400)

    def test_rejects_invalid_status(self):
        task_id = self.post(title="Move me").json()["id"]
        self.assertEqual(self.patch(task_id, status="banana").status_code, 400)

    def test_delete_task(self):
        task_id = self.post(title="Temporary").json()["id"]
        response = self.client.delete(reverse("task_detail", args=[task_id]))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get(reverse("task_list")).json()["tasks"], [])

    def test_move_to_done_updates_stats(self):
        task_id = self.post(title="Write tests").json()["id"]
        self.patch(task_id, status="done")
        stats = self.client.get(reverse("stats")).json()
        self.assertEqual((stats["done"], stats["done_this_week"]), (1, 1))

    def test_moving_out_of_done_clears_weekly_count(self):
        task_id = self.post(title="Reopen me").json()["id"]
        self.patch(task_id, status="done")
        self.patch(task_id, status="doing")
        stats = self.client.get(reverse("stats")).json()
        self.assertEqual((stats["done"], stats["done_this_week"]), (0, 0))

    def test_overdue_counts_only_open_tasks(self):
        self.post(title="Late", due_date="2000-01-01")
        done_id = self.post(title="Late but done", due_date="2000-01-01").json()["id"]
        self.patch(done_id, status="done")
        self.assertEqual(self.client.get(reverse("stats")).json()["overdue"], 1)

    def test_users_cannot_touch_each_others_tasks(self):
        task_id = self.post(title="Private").json()["id"]
        User.objects.create_user("other", password="pass12345")
        self.client.login(username="other", password="pass12345")
        self.assertEqual(self.patch(task_id, status="done").status_code, 404)
        self.assertEqual(self.client.delete(reverse("task_detail", args=[task_id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("task_list")).json()["tasks"], [])