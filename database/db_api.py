import peewee
import main
import logging


db_filename = main.CONF.get('VK', 'db_file', fallback='')
db = peewee.SqliteDatabase(db_filename, pragmas={'journal_mode': 'wal',
                                                 'cache_size': 64,
                                                 'foreign_keys': 1,
                                                 'ignore_check_constraints': 0,
                                                 'synchronous': 0})


class User(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    name = peewee.CharField()
    is_fem = peewee.BooleanField()
    money = peewee.IntegerField(default=0)

    class Meta:
        database = db


class Admins(peewee.Model):
    user = peewee.ForeignKeyField(User, primary_key=True, on_delete='cascade')
    status = peewee.IntegerField(default=0)

    class Meta:
        database = db


class Group(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    name = peewee.CharField()
    add_by = peewee.ForeignKeyField(User)
    accepted = peewee.IntegerField(default=0)
    nsfw = peewee.BooleanField(default=False)
    likes = peewee.IntegerField(default=0)
    views = peewee.IntegerField(default=0)
    subs = peewee.IntegerField(default=0)
    last_update = peewee.IntegerField(default=0)
    last_post = peewee.IntegerField(default=0)
    last_scan = peewee.IntegerField(default=0)

    class Meta:
        database = db


class Price(peewee.Model):
    group = peewee.ForeignKeyField(Group, primary_key=True, on_delete='cascade')
    add_by = peewee.ForeignKeyField(User)
    accepted = peewee.IntegerField(default=0)
    last_scan = peewee.IntegerField(default=0)
    head = peewee.IntegerField(default=0)
    half = peewee.IntegerField(default=0)
    full = peewee.IntegerField(default=0)

    class Meta:
        database = db


class Art(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    vk_id = peewee.CharField(unique=True)
    url = peewee.CharField(unique=True)
    source = peewee.CharField()
    add_by = peewee.ForeignKeyField(User)
    from_group = peewee.ForeignKeyField(Group, on_delete='cascade')
    accepted = peewee.IntegerField(default=0)
    add_time = peewee.IntegerField(default=0)
    message_id = peewee.IntegerField(default=0)

    class Meta:
        database = db


class Tag(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    title = peewee.CharField(default='None')
    description = peewee.CharField(default='None')

    class Meta:
        database = db


class ArtTag(peewee.Model):
    art = peewee.ForeignKeyField(Art, on_delete='cascade')
    tag = peewee.ForeignKeyField(Tag, on_delete='cascade')

    class Meta:
        database = db
        primary_key = peewee.CompositeKey('art', 'tag')


class Migrations(peewee.Model):
    id = peewee.IntegerField(primary_key=True)

    class Meta:
        database = db


def init_db():
    if not db.get_tables():
        db.create_tables([User, Group, Admins, Migrations, Art, Tag, ArtTag, Price])
        Migrations.create(id=1)
        Migrations.create(id=2)
        Migrations.create(id=3)
        return True
    return False


def update_admins(admin_list):
    for admin in admin_list:
        if admin['role'] in ['creator', 'administrator']:
            user = User.get_or_none(id=admin['id'])
            if user:
                if not Admins.get_or_none(user=user):
                    Admins.create(user=user)


def update_db():
    import playhouse.migrate as playhouse_migrate

    db_migrate = peewee.SqliteDatabase(db_filename, pragmas={'journal_mode': 'wal',
                                                             'cache_size': 64,
                                                             'foreign_keys': 0,
                                                             'ignore_check_constraints': 0,
                                                             'synchronous': 0})
    migrator = playhouse_migrate.SqliteMigrator(db_migrate)
    if not Migrations.get_or_none(1):
        logging.info(f'migration 1')
        playhouse_migrate.migrate(
            migrator.add_column('Group', 'accepted', peewee.BooleanField(default=False)),
        )
        Migrations.create(id=1)
    if not Migrations.get_or_none(2):
        logging.info(f'migration 2')
        playhouse_migrate.migrate(
            migrator.add_column('Group', 'last_scan', Group.last_scan),
            migrator.add_column('Art', 'message_id', Art.message_id),
        )
        Migrations.create(id=2)
    if not Migrations.get_or_none(3):
        logging.info(f'migration 3')
        db.create_tables([Price])
        Migrations.create(id=3)
    #         playhouse_migrate.migrate(
    #             migrator.add_column('RpProfile', 'show_link', RpProfile.show_link),
    #             # migrator.rename_column('ProfileSettingList', 'item_id', 'item'),
    #             # migrator.drop_column('RoleOffer', 'to_profile_id')
    #         )


if __name__ == "__main__":
    update_db()
    pass
