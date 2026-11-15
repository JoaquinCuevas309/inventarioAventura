CREATE DATABASE IF NOT EXISTS `inventarioaventura` DEFAULT CHARACTER SET utf8mb4;
USE `inventarioaventura`;
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE `django_migrations` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `app` varchar(255) NOT NULL, `name` varchar(255) NOT NULL, `applied` datetime(6) NOT NULL);

CREATE TABLE `django_content_type` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(100) NOT NULL, `app_label` varchar(100) NOT NULL, `model` varchar(100) NOT NULL);

ALTER TABLE `django_content_type` ADD CONSTRAINT `django_content_type_app_label_model_76bd3d3b_uniq` UNIQUE (`app_label`, `model`);

ALTER TABLE `django_content_type` MODIFY `name` varchar(100) NULL;

ALTER TABLE `django_content_type` DROP COLUMN `name`;

CREATE TABLE `auth_permission` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(50) NOT NULL, `content_type_id` integer NOT NULL, `codename` varchar(100) NOT NULL);

CREATE TABLE `auth_group` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(80) NOT NULL UNIQUE);

CREATE TABLE `auth_group_permissions` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `group_id` integer NOT NULL, `permission_id` integer NOT NULL);

ALTER TABLE `auth_permission` ADD CONSTRAINT `auth_permission_content_type_id_codename_01ab375a_uniq` UNIQUE (`content_type_id`, `codename`);

ALTER TABLE `auth_permission` ADD CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);

ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` UNIQUE (`group_id`, `permission_id`);

ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);

ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`);

ALTER TABLE `auth_permission` MODIFY `name` varchar(255) NOT NULL;

ALTER TABLE `auth_group` MODIFY `name` varchar(150) NOT NULL;

CREATE TABLE `cuentas_usuario` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `password` varchar(128) NOT NULL, `last_login` datetime(6) NULL, `is_superuser` bool NOT NULL, `username` varchar(150) NOT NULL UNIQUE, `first_name` varchar(150) NOT NULL, `last_name` varchar(150) NOT NULL, `email` varchar(254) NOT NULL, `is_staff` bool NOT NULL, `is_active` bool NOT NULL, `date_joined` datetime(6) NOT NULL, `rol` varchar(20) NOT NULL, `telefono` varchar(20) NOT NULL);

CREATE TABLE `cuentas_usuario_groups` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `usuario_id` bigint NOT NULL, `group_id` integer NOT NULL);

CREATE TABLE `cuentas_usuario_user_permissions` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `usuario_id` bigint NOT NULL, `permission_id` integer NOT NULL);

ALTER TABLE `cuentas_usuario_groups` ADD CONSTRAINT `cuentas_usuario_groups_usuario_id_group_id_f5ef6c73_uniq` UNIQUE (`usuario_id`, `group_id`);

ALTER TABLE `cuentas_usuario_groups` ADD CONSTRAINT `cuentas_usuario_groups_usuario_id_251ff583_fk_cuentas_usuario_id` FOREIGN KEY (`usuario_id`) REFERENCES `cuentas_usuario` (`id`);

ALTER TABLE `cuentas_usuario_groups` ADD CONSTRAINT `cuentas_usuario_groups_group_id_e6725cc8_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);

ALTER TABLE `cuentas_usuario_user_permissions` ADD CONSTRAINT `cuentas_usuario_user_per_usuario_id_permission_id_26c0acea_uniq` UNIQUE (`usuario_id`, `permission_id`);

ALTER TABLE `cuentas_usuario_user_permissions` ADD CONSTRAINT `cuentas_usuario_user_usuario_id_5a9718f1_fk_cuentas_u` FOREIGN KEY (`usuario_id`) REFERENCES `cuentas_usuario` (`id`);

ALTER TABLE `cuentas_usuario_user_permissions` ADD CONSTRAINT `cuentas_usuario_user_permission_id_1753ad79_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`);

CREATE TABLE `django_admin_log` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `action_time` datetime(6) NOT NULL, `object_id` longtext NULL, `object_repr` varchar(200) NOT NULL, `action_flag` smallint UNSIGNED NOT NULL CHECK (`action_flag` >= 0), `change_message` longtext NOT NULL, `content_type_id` integer NULL, `user_id` bigint NOT NULL);

ALTER TABLE `django_admin_log` ADD CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);

ALTER TABLE `django_admin_log` ADD CONSTRAINT `django_admin_log_user_id_c564eba6_fk_cuentas_usuario_id` FOREIGN KEY (`user_id`) REFERENCES `cuentas_usuario` (`id`);

CREATE TABLE `experiencias_categoria` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `nombre` varchar(100) NOT NULL UNIQUE, `descripcion` longtext NOT NULL, `activo` bool NOT NULL);

CREATE TABLE `experiencias_experiencia` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `titulo` varchar(150) NOT NULL, `descripcion` longtext NOT NULL, `precio` integer UNSIGNED NOT NULL CHECK (`precio` >= 0), `cupo_maximo` integer UNSIGNED NOT NULL CHECK (`cupo_maximo` >= 0), `fecha_hora` datetime(6) NOT NULL, `activa` bool NOT NULL, `categoria_id` bigint NOT NULL, `creador_id` bigint NOT NULL);

CREATE TABLE `experiencias_inscripcion` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `fecha_inscripcion` datetime(6) NOT NULL, `estado_pago` varchar(20) NOT NULL, `experiencia_id` bigint NOT NULL, `usuario_id` bigint NOT NULL);

ALTER TABLE `experiencias_experiencia` ADD CONSTRAINT `experiencias_experie_categoria_id_b03f452f_fk_experienc` FOREIGN KEY (`categoria_id`) REFERENCES `experiencias_categoria` (`id`);

ALTER TABLE `experiencias_experiencia` ADD CONSTRAINT `experiencias_experie_creador_id_70b19025_fk_cuentas_u` FOREIGN KEY (`creador_id`) REFERENCES `cuentas_usuario` (`id`);

ALTER TABLE `experiencias_inscripcion` ADD CONSTRAINT `experiencias_inscripcion_usuario_id_experiencia_id_996e38c7_uniq` UNIQUE (`usuario_id`, `experiencia_id`);

ALTER TABLE `experiencias_inscripcion` ADD CONSTRAINT `experiencias_inscrip_experiencia_id_2fbecc6b_fk_experienc` FOREIGN KEY (`experiencia_id`) REFERENCES `experiencias_experiencia` (`id`);

ALTER TABLE `experiencias_inscripcion` ADD CONSTRAINT `experiencias_inscrip_usuario_id_9d6f5da2_fk_cuentas_u` FOREIGN KEY (`usuario_id`) REFERENCES `cuentas_usuario` (`id`);

CREATE TABLE `django_session` (`session_key` varchar(40) NOT NULL PRIMARY KEY, `session_data` longtext NOT NULL, `expire_date` datetime(6) NOT NULL);

CREATE INDEX `django_session_expire_date_a5c62663` ON `django_session` (`expire_date`);

INSERT INTO `django_migrations` (`id`, `app`, `name`, `applied`) VALUES
(1, 'contenttypes', '0001_initial', '2026-11-15 21:53:28.170557'),
(2, 'contenttypes', '0002_remove_content_type_name', '2026-11-15 21:53:28.183404'),
(3, 'auth', '0001_initial', '2026-11-15 21:53:28.207145'),
(4, 'auth', '0002_alter_permission_name_max_length', '2026-11-15 21:53:28.221610'),
(5, 'auth', '0003_alter_user_email_max_length', '2026-11-15 21:53:28.230668'),
(6, 'auth', '0004_alter_user_username_opts', '2026-11-15 21:53:28.241018'),
(7, 'auth', '0005_alter_user_last_login_null', '2026-11-15 21:53:28.250874'),
(8, 'auth', '0006_require_contenttypes_0002', '2026-11-15 21:53:28.257032'),
(9, 'auth', '0007_alter_validators_add_error_messages', '2026-11-15 21:53:28.267544'),
(10, 'auth', '0008_alter_user_username_max_length', '2026-11-15 21:53:28.277970'),
(11, 'auth', '0009_alter_user_last_name_max_length', '2026-11-15 21:53:28.288485'),
(12, 'auth', '0010_alter_group_name_max_length', '2026-11-15 21:53:28.305693'),
(13, 'auth', '0011_update_proxy_permissions', '2026-11-15 21:53:28.317422'),
(14, 'auth', '0012_alter_user_first_name_max_length', '2026-11-15 21:53:28.329138'),
(15, 'cuentas', '0001_initial', '2026-11-15 21:53:28.350088'),
(16, 'admin', '0001_initial', '2026-11-15 21:53:28.369285'),
(17, 'admin', '0002_logentry_remove_auto_add', '2026-11-15 21:53:28.386763'),
(18, 'admin', '0003_logentry_add_action_flag_choices', '2026-11-15 21:53:28.399688'),
(19, 'experiencias', '0001_initial', '2026-11-15 21:53:28.435379'),
(20, 'sessions', '0001_initial', '2026-11-15 21:53:28.447760');

INSERT INTO `django_content_type` (`id`, `app_label`, `model`) VALUES
(1, 'admin', 'logentry'),
(2, 'auth', 'group'),
(3, 'auth', 'permission'),
(4, 'contenttypes', 'contenttype'),
(5, 'sessions', 'session'),
(6, 'cuentas', 'usuario'),
(7, 'experiencias', 'categoria'),
(8, 'experiencias', 'experiencia'),
(9, 'experiencias', 'inscripcion');

INSERT INTO `auth_permission` (`id`, `content_type_id`, `codename`, `name`) VALUES
(1, 1, 'add_logentry', 'Can add log entry'),
(2, 1, 'change_logentry', 'Can change log entry'),
(3, 1, 'delete_logentry', 'Can delete log entry'),
(4, 1, 'view_logentry', 'Can view log entry'),
(5, 3, 'add_permission', 'Can add permission'),
(6, 3, 'change_permission', 'Can change permission'),
(7, 3, 'delete_permission', 'Can delete permission'),
(8, 3, 'view_permission', 'Can view permission'),
(9, 2, 'add_group', 'Can add group'),
(10, 2, 'change_group', 'Can change group'),
(11, 2, 'delete_group', 'Can delete group'),
(12, 2, 'view_group', 'Can view group'),
(13, 4, 'add_contenttype', 'Can add content type'),
(14, 4, 'change_contenttype', 'Can change content type'),
(15, 4, 'delete_contenttype', 'Can delete content type'),
(16, 4, 'view_contenttype', 'Can view content type'),
(17, 5, 'add_session', 'Can add session'),
(18, 5, 'change_session', 'Can change session'),
(19, 5, 'delete_session', 'Can delete session'),
(20, 5, 'view_session', 'Can view session'),
(21, 6, 'add_usuario', 'Can add user'),
(22, 6, 'change_usuario', 'Can change user'),
(23, 6, 'delete_usuario', 'Can delete user'),
(24, 6, 'view_usuario', 'Can view user'),
(25, 7, 'add_categoria', 'Can add Categoria'),
(26, 7, 'change_categoria', 'Can change Categoria'),
(27, 7, 'delete_categoria', 'Can delete Categoria'),
(28, 7, 'view_categoria', 'Can view Categoria'),
(29, 8, 'add_experiencia', 'Can add Experiencia'),
(30, 8, 'change_experiencia', 'Can change Experiencia'),
(31, 8, 'delete_experiencia', 'Can delete Experiencia'),
(32, 8, 'view_experiencia', 'Can view Experiencia'),
(33, 9, 'add_inscripcion', 'Can add Inscripcion'),
(34, 9, 'change_inscripcion', 'Can change Inscripcion'),
(35, 9, 'delete_inscripcion', 'Can delete Inscripcion'),
(36, 9, 'view_inscripcion', 'Can view Inscripcion');

INSERT INTO `cuentas_usuario` (`id`, `password`, `last_login`, `is_superuser`, `username`, `first_name`, `last_name`, `email`, `is_staff`, `is_active`, `date_joined`, `rol`, `telefono`) VALUES
(1, 'pbkdf2_sha256$1500000$r2Wjv3VidC1aaHm5Nxr9N8$gopqfeab2IFly+CIHSsbbXQ9Da/arkPmLL9oH0oMERE=', NULL, 1, 'admin_aventura', 'Admin', 'Aventura', 'admin@aventuradelsur.cl', 1, 1, '2026-11-15 21:53:30.310301', 'admin', ''),
(2, 'pbkdf2_sha256$1500000$aZxD8tiAZQ8iWVhIrDEFtS$5YWexRAFgDLxMaUzdZsIu0gvVVjdzO5qL/gDdxaLSTs=', NULL, 0, 'guia_marcela', 'Marcela', 'Rojas', 'guia_marcela@aventuradelsur.cl', 0, 1, '2026-11-15 21:53:31.480920', 'guia', ''),
(3, 'pbkdf2_sha256$1500000$iuCy9FqKQMCJHJdPEe02rt$z32ipegjZFWx/D2gPuV2Awsp0czCTXrjS81kzXh2rBA=', NULL, 0, 'guia_tomas', 'Tomas', 'Vidal', 'guia_tomas@aventuradelsur.cl', 0, 1, '2026-11-15 21:53:32.831385', 'guia', ''),
(4, 'pbkdf2_sha256$1500000$hq4i4lkyoryFYFI205T0VQ$7KP7VU2vlFG9ECGFxINH2UnoEKJBO1IW5VQeGDNSAMc=', NULL, 0, 'turista_ana', 'Ana', 'Soto', 'turista_ana@correo.cl', 0, 1, '2026-11-15 21:53:34.208299', 'turista', ''),
(5, 'pbkdf2_sha256$1500000$AOmHHOUkqb86B0gWIeNRfM$0pzYML7EN/Wy9O6kQw++otU85IuZSQ+uREgBNTR8G+4=', NULL, 0, 'turista_luis', 'Luis', 'Pino', 'turista_luis@correo.cl', 0, 1, '2026-11-15 21:53:35.598969', 'turista', '');

INSERT INTO `experiencias_categoria` (`id`, `nombre`, `descripcion`, `activo`) VALUES
(1, 'Trekking', 'Rutas de caminata guiadas por senderos del ecoparque.', 1),
(2, 'Canopy', 'Circuitos de tirolesas entre los arboles nativos.', 1),
(3, 'Arriendo de equipos', 'Arriendo de equipo tecnico para actividades al aire libre.', 1),
(4, 'Kayak', 'Recorridos en kayak por el lago y el rio.', 1);

INSERT INTO `experiencias_experiencia` (`id`, `titulo`, `descripcion`, `precio`, `cupo_maximo`, `fecha_hora`, `activa`, `categoria_id`, `creador_id`) VALUES
(1, 'Trekking Sendero del Bosque Nativo', 'Trekking Sendero del Bosque Nativo. Actividad guiada con equipo de seguridad incluido.', 12000, 15, '2027-02-13 21:53:37.204664', 1, 1, 2),
(2, 'Trekking Cumbre del Mirador', 'Trekking Cumbre del Mirador. Actividad guiada con equipo de seguridad incluido.', 18000, 10, '2027-02-14 21:53:37.204664', 1, 1, 2),
(3, 'Canopy Circuito Alto', 'Canopy Circuito Alto. Actividad guiada con equipo de seguridad incluido.', 25000, 8, '2027-02-15 21:53:37.204664', 1, 2, 2),
(4, 'Arriendo de Equipo Completo de Montaña', 'Arriendo de Equipo Completo de Montaña. Actividad guiada con equipo de seguridad incluido.', 9000, 20, '2027-02-16 21:53:37.204664', 1, 3, 2),
(5, 'Kayak Laguna Esmeralda', 'Kayak Laguna Esmeralda. Actividad guiada con equipo de seguridad incluido.', 20000, 12, '2027-02-17 21:53:37.204664', 1, 4, 3),
(6, 'Kayak Rio Sereno al Atardecer', 'Kayak Rio Sereno al Atardecer. Actividad guiada con equipo de seguridad incluido.', 22000, 10, '2027-02-18 21:53:37.204664', 1, 4, 3),
(7, 'Canopy Circuito Infantil', 'Canopy Circuito Infantil. Actividad guiada con equipo de seguridad incluido.', 15000, 12, '2027-02-19 21:53:37.204664', 1, 2, 3),
(8, 'Trekking Nocturno de Fauna', 'Trekking Nocturno de Fauna. Actividad guiada con equipo de seguridad incluido.', 16000, 8, '2027-02-20 21:53:37.204664', 1, 1, 3);

INSERT INTO `experiencias_inscripcion` (`id`, `fecha_inscripcion`, `estado_pago`, `experiencia_id`, `usuario_id`) VALUES
(1, '2026-11-15 21:53:37.284420', 'confirmado', 1, 4),
(2, '2026-11-15 21:53:37.296118', 'pendiente', 2, 4),
(3, '2026-11-15 21:53:37.307477', 'pendiente', 3, 4),
(4, '2026-11-15 21:53:37.317341', 'confirmado', 4, 5),
(5, '2026-11-15 21:53:37.327001', 'pendiente', 5, 5),
(6, '2026-11-15 21:53:37.336356', 'pendiente', 6, 5);

SET FOREIGN_KEY_CHECKS = 1;
