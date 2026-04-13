SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `project_taskly` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `project_taskly`;

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
);

CREATE TABLE IF NOT EXISTS `auth_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
);

CREATE TABLE IF NOT EXISTS `auth_group_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
);

CREATE TABLE IF NOT EXISTS `auth_permission` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=77 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

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
);

CREATE TABLE IF NOT EXISTS `auth_user_groups` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
);

CREATE TABLE IF NOT EXISTS `auth_user_user_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
);

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
);

CREATE TABLE IF NOT EXISTS `django_content_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

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

CREATE TABLE IF NOT EXISTS `django_migrations` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
);

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

CREATE TABLE IF NOT EXISTS `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
);

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
);

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
);

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
);

CREATE TABLE IF NOT EXISTS `expense_categories` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `project_id` int(11) NOT NULL,
  `is_fixed` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `expense_categories_project_id_name_3f2f1802_uniq` (`project_id`,`name`),
  CONSTRAINT `expense_categories_project_id_ba08e283_fk_projects_id` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`)
);

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
);

CREATE TABLE IF NOT EXISTS `password_otps` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `email` varchar(254) NOT NULL,
  `otp_hash` varchar(128) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `expires_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `password_otps_email_2b91daf4` (`email`)
);

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
);

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
);

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
);

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
);

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
);

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
);

SET FOREIGN_KEY_CHECKS = 1;