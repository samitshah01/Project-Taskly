-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Server version:               11.8.6-MariaDB - MariaDB Server
-- Server OS:                    Win64
-- HeidiSQL Version:             12.17.0.7270
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Dumping database structure for project_taskly
CREATE DATABASE IF NOT EXISTS `project_taskly` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci */;
USE `project_taskly`;

-- Dumping structure for table project_taskly.activity_logs
CREATE TABLE IF NOT EXISTS `activity_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `action` varchar(255) NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  `project_id` int(11) DEFAULT NULL,
  `task_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `activity_logs_project_id_5df13a8e_fk_projects_id` (`project_id`),
  KEY `activity_logs_task_id_7e0399c3_fk_tasks_id` (`task_id`),
  KEY `activity_logs_user_id_60cbbbe3_fk_users_id` (`user_id`),
  CONSTRAINT `activity_logs_project_id_5df13a8e_fk_projects_id` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`),
  CONSTRAINT `activity_logs_task_id_7e0399c3_fk_tasks_id` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`),
  CONSTRAINT `activity_logs_user_id_60cbbbe3_fk_users_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.activity_logs: ~11 rows (approximately)
INSERT INTO `activity_logs` (`id`, `action`, `timestamp`, `project_id`, `task_id`, `user_id`) VALUES
	(1, 'created project "Website Development"', '2026-05-01 03:28:12.035959', 1, NULL, 8),
	(2, 'created task "Initialize the landing page"', '2026-05-01 03:28:57.782801', 1, 1, 8),
	(3, 'moved task "Initialize the landing page" to In Progress', '2026-05-01 03:29:01.093644', 1, 1, 8),
	(4, 'moved task "Initialize the landing page" to To Do', '2026-05-01 03:29:01.561755', 1, 1, 8),
	(5, 'created task "test"', '2026-05-01 03:29:07.371347', 1, 2, 8),
	(6, 'moved task "test" to In Progress', '2026-05-01 03:29:21.838895', 1, 2, 8),
	(7, 'moved task "test" to Completed', '2026-05-01 03:29:22.460259', 1, 2, 8),
	(8, 'moved task "test" to In Progress', '2026-05-01 03:29:23.031630', 1, 2, 8),
	(9, 'moved task "test" to To Do', '2026-05-01 03:29:23.711427', 1, 2, 8),
	(10, 'added a salary payment transaction for "Website Development"', '2026-05-01 03:30:21.906139', 1, NULL, 8),
	(11, 'added a income transaction for "Website Development"', '2026-05-01 03:31:01.299453', 1, NULL, 8);

-- Dumping structure for table project_taskly.auth_group
CREATE TABLE IF NOT EXISTS `auth_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.auth_group: ~0 rows (approximately)

-- Dumping structure for table project_taskly.auth_group_permissions
CREATE TABLE IF NOT EXISTS `auth_group_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.auth_group_permissions: ~0 rows (approximately)

-- Dumping structure for table project_taskly.auth_permission
CREATE TABLE IF NOT EXISTS `auth_permission` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=77 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

-- Dumping data for table project_taskly.auth_permission: ~76 rows (approximately)
INSERT INTO `auth_permission` (`id`, `name`, `content_type_id`, `codename`) VALUES
	(1, 'Can add log entry', 1, 'add_logentry'),
	(2, 'Can change log entry', 1, 'change_logentry'),
	(3, 'Can delete log entry', 1, 'delete_logentry'),
	(4, 'Can view log entry', 1, 'view_logentry'),
	(5, 'Can add permission', 2, 'add_permission'),
	(6, 'Can change permission', 2, 'change_permission'),
	(7, 'Can delete permission', 2, 'delete_permission'),
	(8, 'Can view permission', 2, 'view_permission'),
	(9, 'Can add group', 3, 'add_group'),
	(10, 'Can change group', 3, 'change_group'),
	(11, 'Can delete group', 3, 'delete_group'),
	(12, 'Can view group', 3, 'view_group'),
	(13, 'Can add user', 4, 'add_user'),
	(14, 'Can change user', 4, 'change_user'),
	(15, 'Can delete user', 4, 'delete_user'),
	(16, 'Can view user', 4, 'view_user'),
	(17, 'Can add content type', 5, 'add_contenttype'),
	(18, 'Can change content type', 5, 'change_contenttype'),
	(19, 'Can delete content type', 5, 'delete_contenttype'),
	(20, 'Can view content type', 5, 'view_contenttype'),
	(21, 'Can add session', 6, 'add_session'),
	(22, 'Can change session', 6, 'change_session'),
	(23, 'Can delete session', 6, 'delete_session'),
	(24, 'Can view session', 6, 'view_session'),
	(25, 'Can add password otp', 7, 'add_passwordotp'),
	(26, 'Can change password otp', 7, 'change_passwordotp'),
	(27, 'Can delete password otp', 7, 'delete_passwordotp'),
	(28, 'Can view password otp', 7, 'view_passwordotp'),
	(29, 'Can add project', 8, 'add_project'),
	(30, 'Can change project', 8, 'change_project'),
	(31, 'Can delete project', 8, 'delete_project'),
	(32, 'Can view project', 8, 'view_project'),
	(33, 'Can add task', 9, 'add_task'),
	(34, 'Can change task', 9, 'change_task'),
	(35, 'Can delete task', 9, 'delete_task'),
	(36, 'Can view task', 9, 'view_task'),
	(37, 'Can add users', 10, 'add_users'),
	(38, 'Can change users', 10, 'change_users'),
	(39, 'Can delete users', 10, 'delete_users'),
	(40, 'Can view users', 10, 'view_users'),
	(41, 'Can add task comment', 11, 'add_taskcomment'),
	(42, 'Can change task comment', 11, 'change_taskcomment'),
	(43, 'Can delete task comment', 11, 'delete_taskcomment'),
	(44, 'Can view task comment', 11, 'view_taskcomment'),
	(45, 'Can add project file', 12, 'add_projectfile'),
	(46, 'Can change project file', 12, 'change_projectfile'),
	(47, 'Can delete project file', 12, 'delete_projectfile'),
	(48, 'Can view project file', 12, 'view_projectfile'),
	(49, 'Can add expense', 13, 'add_expense'),
	(50, 'Can change expense', 13, 'change_expense'),
	(51, 'Can delete expense', 13, 'delete_expense'),
	(52, 'Can view expense', 13, 'view_expense'),
	(53, 'Can add activity log', 14, 'add_activitylog'),
	(54, 'Can change activity log', 14, 'change_activitylog'),
	(55, 'Can delete activity log', 14, 'delete_activitylog'),
	(56, 'Can view activity log', 14, 'view_activitylog'),
	(57, 'Can add project member', 15, 'add_projectmember'),
	(58, 'Can change project member', 15, 'change_projectmember'),
	(59, 'Can delete project member', 15, 'delete_projectmember'),
	(60, 'Can view project member', 15, 'view_projectmember'),
	(61, 'Can add expense category', 16, 'add_expensecategory'),
	(62, 'Can change expense category', 16, 'change_expensecategory'),
	(63, 'Can delete expense category', 16, 'delete_expensecategory'),
	(64, 'Can view expense category', 16, 'view_expensecategory'),
	(65, 'Can add employee profile', 17, 'add_employeeprofile'),
	(66, 'Can change employee profile', 17, 'change_employeeprofile'),
	(67, 'Can delete employee profile', 17, 'delete_employeeprofile'),
	(68, 'Can view employee profile', 17, 'view_employeeprofile'),
	(69, 'Can add employee payroll', 18, 'add_employeepayroll'),
	(70, 'Can change employee payroll', 18, 'change_employeepayroll'),
	(71, 'Can delete employee payroll', 18, 'delete_employeepayroll'),
	(72, 'Can view employee payroll', 18, 'view_employeepayroll'),
	(73, 'Can add email notification log', 19, 'add_emailnotificationlog'),
	(74, 'Can change email notification log', 19, 'change_emailnotificationlog'),
	(75, 'Can delete email notification log', 19, 'delete_emailnotificationlog'),
	(76, 'Can view email notification log', 19, 'view_emailnotificationlog');

-- Dumping structure for table project_taskly.auth_user
CREATE TABLE IF NOT EXISTS `auth_user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.auth_user: ~0 rows (approximately)

-- Dumping structure for table project_taskly.auth_user_groups
CREATE TABLE IF NOT EXISTS `auth_user_groups` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.auth_user_groups: ~0 rows (approximately)

-- Dumping structure for table project_taskly.auth_user_user_permissions
CREATE TABLE IF NOT EXISTS `auth_user_user_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.auth_user_user_permissions: ~0 rows (approximately)

-- Dumping structure for table project_taskly.django_admin_log
CREATE TABLE IF NOT EXISTS `django_admin_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext DEFAULT NULL,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) unsigned NOT NULL CHECK (`action_flag` >= 0),
  `change_message` longtext NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.django_admin_log: ~0 rows (approximately)

-- Dumping structure for table project_taskly.django_content_type
CREATE TABLE IF NOT EXISTS `django_content_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

-- Dumping data for table project_taskly.django_content_type: ~19 rows (approximately)
INSERT INTO `django_content_type` (`id`, `app_label`, `model`) VALUES
	(1, 'admin', 'logentry'),
	(2, 'auth', 'permission'),
	(3, 'auth', 'group'),
	(4, 'auth', 'user'),
	(5, 'contenttypes', 'contenttype'),
	(6, 'sessions', 'session'),
	(7, 'project_taskly', 'passwordotp'),
	(8, 'project_taskly', 'project'),
	(9, 'project_taskly', 'task'),
	(10, 'project_taskly', 'users'),
	(11, 'project_taskly', 'taskcomment'),
	(12, 'project_taskly', 'projectfile'),
	(13, 'project_taskly', 'expense'),
	(14, 'project_taskly', 'activitylog'),
	(15, 'project_taskly', 'projectmember'),
	(16, 'project_taskly', 'expensecategory'),
	(17, 'project_taskly', 'employeeprofile'),
	(18, 'project_taskly', 'employeepayroll'),
	(19, 'project_taskly', 'emailnotificationlog');

-- Dumping structure for table project_taskly.django_migrations
CREATE TABLE IF NOT EXISTS `django_migrations` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.django_migrations: ~28 rows (approximately)
INSERT INTO `django_migrations` (`id`, `app`, `name`, `applied`) VALUES
	(1, 'contenttypes', '0001_initial', '2026-04-13 17:46:35.621809'),
	(2, 'auth', '0001_initial', '2026-04-13 17:46:35.864864'),
	(3, 'admin', '0001_initial', '2026-04-13 17:46:35.918877'),
	(4, 'admin', '0002_logentry_remove_auto_add', '2026-04-13 17:46:35.925877'),
	(5, 'admin', '0003_logentry_add_action_flag_choices', '2026-04-13 17:46:35.944882'),
	(6, 'contenttypes', '0002_remove_content_type_name', '2026-04-13 17:46:35.984890'),
	(7, 'auth', '0002_alter_permission_name_max_length', '2026-04-13 17:46:36.008896'),
	(8, 'auth', '0003_alter_user_email_max_length', '2026-04-13 17:46:36.025899'),
	(9, 'auth', '0004_alter_user_username_opts', '2026-04-13 17:46:36.031901'),
	(10, 'auth', '0005_alter_user_last_login_null', '2026-04-13 17:46:36.056907'),
	(11, 'auth', '0006_require_contenttypes_0002', '2026-04-13 17:46:36.060907'),
	(12, 'auth', '0007_alter_validators_add_error_messages', '2026-04-13 17:46:36.066908'),
	(13, 'auth', '0008_alter_user_username_max_length', '2026-04-13 17:46:36.089914'),
	(14, 'auth', '0009_alter_user_last_name_max_length', '2026-04-13 17:46:36.113920'),
	(15, 'auth', '0010_alter_group_name_max_length', '2026-04-13 17:46:36.130923'),
	(16, 'auth', '0011_update_proxy_permissions', '2026-04-13 17:46:36.136925'),
	(17, 'auth', '0012_alter_user_first_name_max_length', '2026-04-13 17:46:36.153928'),
	(18, 'project_taskly', '0001_initial', '2026-04-13 17:46:36.519011'),
	(19, 'project_taskly', '0002_projectmember_is_manager', '2026-04-13 17:46:36.549018'),
	(20, 'project_taskly', '0003_expensecategory_expense_category', '2026-04-13 17:46:36.637037'),
	(21, 'project_taskly', '0004_auto_20260411_2322', '2026-04-13 17:46:36.950108'),
	(22, 'project_taskly', '0005_project_owner_expensecategory_is_fixed', '2026-04-13 17:46:37.013120'),
	(23, 'project_taskly', '0006_expense_assigned_user', '2026-04-13 17:46:37.042128'),
	(24, 'project_taskly', '0007_users_is_email_verified', '2026-04-13 17:46:37.073135'),
	(25, 'project_taskly', '0008_remove_unused_created_by_columns', '2026-04-13 17:46:37.160155'),
	(26, 'project_taskly', '0009_remove_projectmember_allocation_hours_per_day', '2026-04-13 17:46:37.180159'),
	(27, 'project_taskly', '0010_auto_20260413_1948', '2026-04-13 17:46:37.285687'),
	(28, 'sessions', '0001_initial', '2026-04-13 17:46:37.312197');

-- Dumping structure for table project_taskly.django_session
CREATE TABLE IF NOT EXISTS `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.django_session: ~1 rows (approximately)
INSERT INTO `django_session` (`session_key`, `session_data`, `expire_date`) VALUES
	('5ig4oq0h0uc0gq283qiq1bp4hps2t48m', 'e30:1wIecz:q0WmpQ_56RSVnR6gjSHsBQF19sGh3gt6M83VbBL_HQI', '2026-05-31 03:33:21.572685');

-- Dumping structure for table project_taskly.email_notification_logs
CREATE TABLE IF NOT EXISTS `email_notification_logs` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `notification_type` varchar(40) NOT NULL,
  `reminder_stage` smallint(5) unsigned DEFAULT NULL CHECK (`reminder_stage` >= 0),
  `recipient_email` varchar(254) NOT NULL,
  `subject` varchar(255) NOT NULL,
  `idempotency_key` varchar(255) NOT NULL,
  `status` varchar(20) NOT NULL,
  `error_message` longtext DEFAULT NULL,
  `sent_at` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `expense_id` int(11) DEFAULT NULL,
  `task_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idempotency_key` (`idempotency_key`),
  KEY `email_notification_logs_expense_id_f73c4078_fk_expenses_id` (`expense_id`),
  KEY `email_notification_logs_task_id_46050baa_fk_tasks_id` (`task_id`),
  KEY `email_notification_logs_user_id_7e68383f_fk_users_id` (`user_id`),
  CONSTRAINT `email_notification_logs_expense_id_f73c4078_fk_expenses_id` FOREIGN KEY (`expense_id`) REFERENCES `expenses` (`id`),
  CONSTRAINT `email_notification_logs_task_id_46050baa_fk_tasks_id` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`),
  CONSTRAINT `email_notification_logs_user_id_7e68383f_fk_users_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.email_notification_logs: ~4 rows (approximately)
INSERT INTO `email_notification_logs` (`id`, `notification_type`, `reminder_stage`, `recipient_email`, `subject`, `idempotency_key`, `status`, `error_message`, `sent_at`, `created_at`, `updated_at`, `expense_id`, `task_id`, `user_id`) VALUES
	(1, 'welcome', NULL, 'samitshah4444@gmail.com', 'Welcome to Taskly, Samit Shah', 'welcome:8', 'sent', NULL, '2026-05-01 03:26:44.880026', '2026-05-01 03:26:43.761137', '2026-05-01 03:26:44.880026', NULL, NULL, 8),
	(2, 'task_assignment', NULL, 'r@gmail.com', 'Task Assigned: Initialize the landing page', 'task-assignment:1:2:2026-05-01T03:28:57.779301+00:00', 'sent', NULL, '2026-05-01 03:28:58.958217', '2026-05-01 03:28:57.781796', '2026-05-01 03:28:58.958217', NULL, 1, 2),
	(3, 'task_assignment', NULL, 'samitshah4444@gmail.com', 'Task Assigned: test', 'task-assignment:2:8:2026-05-01T03:29:07.366259+00:00', 'sent', NULL, '2026-05-01 03:29:08.489308', '2026-05-01 03:29:07.369239', '2026-05-01 03:29:08.489308', NULL, 2, 8),
	(4, 'payment', NULL, 'r@gmail.com', 'Payment Received: Salary', 'payment:1:2:paid:100:2026-05-02', 'sent', NULL, '2026-05-01 03:30:23.030092', '2026-05-01 03:30:21.900938', '2026-05-01 03:30:23.030092', 1, NULL, 2);

-- Dumping structure for table project_taskly.employee_payroll
CREATE TABLE IF NOT EXISTS `employee_payroll` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `month` date NOT NULL,
  `base_salary` decimal(10,2) NOT NULL,
  `bonus` decimal(10,2) NOT NULL,
  `deduction` decimal(10,2) NOT NULL,
  `payment_status` varchar(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `employee_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `employee_payroll_employee_id_b6d7e37f_fk_employee_profiles_id` (`employee_id`),
  CONSTRAINT `employee_payroll_employee_id_b6d7e37f_fk_employee_profiles_id` FOREIGN KEY (`employee_id`) REFERENCES `employee_profiles` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.employee_payroll: ~0 rows (approximately)

-- Dumping structure for table project_taskly.employee_profiles
CREATE TABLE IF NOT EXISTS `employee_profiles` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `employee_type` varchar(20) NOT NULL,
  `salary` decimal(10,2) NOT NULL,
  `join_date` date NOT NULL,
  `status` varchar(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `employee_profiles_user_id_a490e3b4_fk_users_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.employee_profiles: ~5 rows (approximately)
INSERT INTO `employee_profiles` (`id`, `employee_type`, `salary`, `join_date`, `status`, `user_id`) VALUES
	(1, 'full_time', 0.00, '2026-05-01', 'active', 5),
	(2, 'full_time', 0.00, '2026-05-01', 'active', 1),
	(3, 'full_time', 0.00, '2026-05-01', 'active', 4),
	(4, 'full_time', 0.00, '2026-05-01', 'active', 2),
	(5, 'full_time', 0.00, '2026-05-01', 'active', 8);

-- Dumping structure for table project_taskly.expense_categories
CREATE TABLE IF NOT EXISTS `expense_categories` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `project_id` int(11) NOT NULL,
  `is_fixed` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `expense_categories_project_id_name_3f2f1802_uniq` (`project_id`,`name`),
  CONSTRAINT `expense_categories_project_id_ba08e283_fk_projects_id` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.expense_categories: ~4 rows (approximately)
INSERT INTO `expense_categories` (`id`, `name`, `created_at`, `project_id`, `is_fixed`) VALUES
	(1, 'Salary', '2026-05-01 03:28:12.025429', 1, 1),
	(2, 'Tools', '2026-05-01 03:28:12.026287', 1, 1),
	(3, 'Services', '2026-05-01 03:28:12.027934', 1, 1),
	(4, 'Miscellaneous', '2026-05-01 03:28:12.028939', 1, 1);

-- Dumping structure for table project_taskly.expenses
CREATE TABLE IF NOT EXISTS `expenses` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `amount` decimal(10,2) NOT NULL,
  `description` varchar(255) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `project_id` int(11) NOT NULL,
  `category_id` int(11) DEFAULT NULL,
  `issue_date` date DEFAULT NULL,
  `note` longtext DEFAULT NULL,
  `paid_date` date DEFAULT NULL,
  `reference_id` varchar(120) DEFAULT NULL,
  `status` varchar(20) NOT NULL,
  `title` varchar(255) DEFAULT NULL,
  `transaction_type` varchar(20) NOT NULL,
  `assigned_user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `expenses_project_id_2bce80f6_fk_projects_id` (`project_id`),
  KEY `expenses_category_id_3d2bce2b_fk_expense_categories_id` (`category_id`),
  KEY `expenses_assigned_user_id_33596ca8_fk_users_id` (`assigned_user_id`),
  CONSTRAINT `expenses_assigned_user_id_33596ca8_fk_users_id` FOREIGN KEY (`assigned_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `expenses_category_id_3d2bce2b_fk_expense_categories_id` FOREIGN KEY (`category_id`) REFERENCES `expense_categories` (`id`),
  CONSTRAINT `expenses_project_id_2bce80f6_fk_projects_id` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.expenses: ~2 rows (approximately)
INSERT INTO `expenses` (`id`, `amount`, `description`, `created_at`, `project_id`, `category_id`, `issue_date`, `note`, `paid_date`, `reference_id`, `status`, `title`, `transaction_type`, `assigned_user_id`) VALUES
	(1, 100.00, 'salary payment', '2026-05-01 03:30:21.897793', 1, NULL, '2026-05-01', 'salary payment', '2026-05-02', 'TXN-000001', 'paid', 'Salary', 'expense', 2),
	(2, 500.00, 'testing income', '2026-05-01 03:31:01.297625', 1, NULL, '2026-05-01', NULL, '2026-05-01', 'TXN-000002', 'paid', 'testing income', 'income', NULL);

-- Dumping structure for table project_taskly.password_otps
CREATE TABLE IF NOT EXISTS `password_otps` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `email` varchar(254) NOT NULL,
  `otp_hash` varchar(128) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `expires_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `password_otps_email_2b91daf4` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.password_otps: ~0 rows (approximately)

-- Dumping structure for table project_taskly.project_files
CREATE TABLE IF NOT EXISTS `project_files` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `file` varchar(255) NOT NULL,
  `uploaded_at` datetime(6) NOT NULL,
  `project_id` int(11) NOT NULL,
  `uploaded_by_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `project_files_project_id_2abe4242_fk_projects_id` (`project_id`),
  KEY `project_files_uploaded_by_id_1834e0af_fk_users_id` (`uploaded_by_id`),
  CONSTRAINT `project_files_project_id_2abe4242_fk_projects_id` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`),
  CONSTRAINT `project_files_uploaded_by_id_1834e0af_fk_users_id` FOREIGN KEY (`uploaded_by_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.project_files: ~0 rows (approximately)

-- Dumping structure for table project_taskly.project_members
CREATE TABLE IF NOT EXISTS `project_members` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `role` varchar(100) DEFAULT NULL,
  `joined_at` datetime(6) NOT NULL,
  `project_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `is_manager` tinyint(1) NOT NULL,
  `assignment_end_date` date DEFAULT NULL,
  `assignment_notes` longtext DEFAULT NULL,
  `assignment_start_date` date DEFAULT NULL,
  `assignment_status` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `project_members_project_id_user_id_ab18bfcc_uniq` (`project_id`,`user_id`),
  KEY `project_members_user_id_2e9d44b1_fk_users_id` (`user_id`),
  CONSTRAINT `project_members_project_id_bf2e42ec_fk_projects_id` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`),
  CONSTRAINT `project_members_user_id_2e9d44b1_fk_users_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.project_members: ~5 rows (approximately)
INSERT INTO `project_members` (`id`, `role`, `joined_at`, `project_id`, `user_id`, `is_manager`, `assignment_end_date`, `assignment_notes`, `assignment_start_date`, `assignment_status`) VALUES
	(1, 'Project Manager', '2026-05-01 03:28:12.023362', 1, 8, 1, NULL, NULL, NULL, 'active'),
	(2, 'Designer', '2026-05-01 03:28:12.032451', 1, 1, 0, NULL, NULL, NULL, 'active'),
	(3, 'Developer', '2026-05-01 03:28:12.033449', 1, 2, 0, NULL, NULL, NULL, 'active'),
	(4, 'QA Engineer', '2026-05-01 03:28:12.034450', 1, 4, 0, NULL, NULL, NULL, 'active'),
	(5, 'Client', '2026-05-01 03:28:12.034954', 1, 5, 0, NULL, NULL, NULL, 'active');

-- Dumping structure for table project_taskly.projects
CREATE TABLE IF NOT EXISTS `projects` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `description` longtext DEFAULT NULL,
  `start_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `budget` decimal(12,2) NOT NULL,
  `status` varchar(20) NOT NULL,
  `color` varchar(20) NOT NULL,
  `icon` varchar(50) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `manager_id` int(11) DEFAULT NULL,
  `owner_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `projects_manager_id_a2bc48df_fk_users_id` (`manager_id`),
  KEY `projects_owner_id_a6ce54bc_fk_users_id` (`owner_id`),
  CONSTRAINT `projects_manager_id_a2bc48df_fk_users_id` FOREIGN KEY (`manager_id`) REFERENCES `users` (`id`),
  CONSTRAINT `projects_owner_id_a6ce54bc_fk_users_id` FOREIGN KEY (`owner_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.projects: ~1 rows (approximately)
INSERT INTO `projects` (`id`, `name`, `description`, `start_date`, `end_date`, `budget`, `status`, `color`, `icon`, `created_at`, `updated_at`, `manager_id`, `owner_id`) VALUES
	(1, 'Website Development', 'Full stack development', '2026-05-01', '2026-05-09', 5000.00, 'planned', '#7c5cfc', 'globe', '2026-05-01 03:28:12.020355', '2026-05-01 03:28:12.020355', 8, 8);

-- Dumping structure for table project_taskly.task_comments
CREATE TABLE IF NOT EXISTS `task_comments` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `comment` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `task_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `task_comments_task_id_774b925c_fk_tasks_id` (`task_id`),
  KEY `task_comments_user_id_d90b57c8_fk_users_id` (`user_id`),
  CONSTRAINT `task_comments_task_id_774b925c_fk_tasks_id` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`),
  CONSTRAINT `task_comments_user_id_d90b57c8_fk_users_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.task_comments: ~0 rows (approximately)

-- Dumping structure for table project_taskly.tasks
CREATE TABLE IF NOT EXISTS `tasks` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `description` longtext DEFAULT NULL,
  `status` varchar(20) NOT NULL,
  `priority` varchar(10) NOT NULL,
  `due_date` date DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `assigned_to_id` int(11) DEFAULT NULL,
  `project_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `tasks_assigned_to_id_942feeaf_fk_users_id` (`assigned_to_id`),
  KEY `tasks_project_id_288f49d9_fk_projects_id` (`project_id`),
  CONSTRAINT `tasks_assigned_to_id_942feeaf_fk_users_id` FOREIGN KEY (`assigned_to_id`) REFERENCES `users` (`id`),
  CONSTRAINT `tasks_project_id_288f49d9_fk_projects_id` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.tasks: ~2 rows (approximately)
INSERT INTO `tasks` (`id`, `title`, `description`, `status`, `priority`, `due_date`, `created_at`, `updated_at`, `assigned_to_id`, `project_id`) VALUES
	(1, 'Initialize the landing page', NULL, 'todo', 'medium', NULL, '2026-05-01 03:28:57.779301', '2026-05-01 03:29:01.561755', 2, 1),
	(2, 'test', NULL, 'todo', 'medium', NULL, '2026-05-01 03:29:07.366259', '2026-05-01 03:29:23.709919', 8, 1);

-- Dumping structure for table project_taskly.users
CREATE TABLE IF NOT EXISTS `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `first_name` varchar(100) DEFAULT NULL,
  `last_name` varchar(100) DEFAULT NULL,
  `username` varchar(50) DEFAULT NULL,
  `email` varchar(150) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` varchar(50) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `is_email_verified` tinyint(1) NOT NULL,
  `email_notifications_enabled` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table project_taskly.users: ~5 rows (approximately)
INSERT INTO `users` (`id`, `first_name`, `last_name`, `username`, `email`, `password`, `role`, `created_at`, `is_email_verified`, `email_notifications_enabled`) VALUES
	(1, 'Kiltan', 'Bimali', 'kiltan', 'kb@gmail.com', 'pbkdf2_sha256$260000$pFFPu2TAdrDESWqdnLQNQI$fG+q1kmCL5wvp1r63f9h7NeDH6NQ6Yx7yWxfTQMOX54=', 'user', '2026-05-01 03:10:58.536453', 1, 1),
	(2, 'Ram', 'Shrestha', 'ram', 'r@gmail.com', 'pbkdf2_sha256$260000$pFFPu2TAdrDESWqdnLQNQI$fG+q1kmCL5wvp1r63f9h7NeDH6NQ6Yx7yWxfTQMOX54=', 'user', '2026-05-01 03:10:58.536453', 1, 1),
	(4, 'Krishna', 'Khatri', 'krishna', 'k@gmail.com', 'pbkdf2_sha256$260000$pFFPu2TAdrDESWqdnLQNQI$fG+q1kmCL5wvp1r63f9h7NeDH6NQ6Yx7yWxfTQMOX54=', 'user', '2026-05-01 03:10:58.536453', 1, 1),
	(5, 'Emperor', 'Jerong', 'emperor', 'ej@gmail.com', 'pbkdf2_sha256$260000$pFFPu2TAdrDESWqdnLQNQI$fG+q1kmCL5wvp1r63f9h7NeDH6NQ6Yx7yWxfTQMOX54=', 'user', '2026-05-01 03:10:58.536453', 1, 1),
	(8, 'Samit', 'Shah', 'samit', 'samitshah4444@gmail.com', 'pbkdf2_sha256$260000$k6aFg44tzYtJ2Pc6xvB1PH$cbzuJLlwe5U5anAH9w5gQGIFbiFG/Hj1y08kzsu7XEo=', 'user', '2026-05-01 03:26:18.423678', 1, 1);

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
