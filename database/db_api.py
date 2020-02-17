import peewee
import logging
import json
import time
from api.Keys import Keys

db_filename = Keys().get_db_filename()
db = peewee.SqliteDatabase(db_filename, pragmas={'journal_mode': 'wal',
                                                 'cache_size': 64,
                                                 'foreign_keys': 1,
                                                 'ignore_check_constraints': 0,
                                                 'synchronous': 0})
profile_actual_time = 31 * 24 * 60 * 60


class User(peewee.Model):
    id = peewee.IntegerField(unique=True)
    name = peewee.CharField()
    is_fem = peewee.BooleanField()
    money = peewee.IntegerField(default=0)
    menu_id = peewee.CharField(default='main')
    item_id = peewee.IntegerField(default=-1)
    tmp_item_id = peewee.IntegerField(default=-1)
    list_iter = peewee.IntegerField(default=0)
    is_admin = peewee.IntegerField(default=0)

    class Meta:
        database = db

    def get_user(self, user_id):
        try:
            user = self.get(self._schema.model.id == user_id)
            return user
        except self.DoesNotExist:
            return False

    def create_user(self, user_id, name, is_fem):
        try:
            new_user = self.create(id=user_id, name=name, is_fem=is_fem)
            return new_user
        except peewee.IntegrityError:
            return self.get_user(user_id)

    def default_settings(self, user_id):
        user = self.get_user(user_id)
        if user:
            user.menu_id = 'main'
            user.item_id = -1
            user.tmp_item_id = -1
            user.list_iter = 0
            user.save()


class RpProfile(peewee.Model):
    search_preset = peewee.BooleanField(default=False)
    owner_id = peewee.IntegerField()
    name = peewee.CharField(default='Не указано')
    description = peewee.CharField(default='')
    arts = peewee.CharField(default='[]')
    create_date = peewee.IntegerField(default=0)
    show_link = peewee.BooleanField(default=0)

    class Meta:
        database = db

    def get_profile(self, profile_id):
        try:
            rp_profile = self.get(self._schema.model.id == profile_id)
            return rp_profile
        except self.DoesNotExist:
            return False

    def get_user_profiles(self, owner_id, search_preset=False):
        try:
            profiles = self.select().where((self._schema.model.owner_id == owner_id) &
                                           (self._schema.model.search_preset == search_preset))
            return profiles
        except self.DoesNotExist:
            return []

    def create_profile(self, user_id, search_preset=False):
        new_rp_profile = self.create(owner_id=user_id, search_preset=search_preset, create_date=int(time.time()))
        return new_rp_profile

    def delete_profile(self, profile_id):
        try:
            delete_profile = self.delete().where(self._schema.model.id == profile_id)
            delete_profile.execute()
            return True
        except self.DoesNotExist:
            return False


class RoleOffer(peewee.Model):
    from_owner_id = peewee.IntegerField()
    to_owner_id = peewee.IntegerField()
    actual = peewee.BooleanField(default=True)

    class Meta:
        database = db
        primary_key = peewee.CompositeKey('from_owner_id', 'to_owner_id')

    def create_offer(self, from_owner_id, to_profile_id):
        try:
            to_owner_id = RpProfile().get_profile(to_profile_id).owner_id
            new_rp_offer = self.create(from_owner_id=from_owner_id,
                                       to_owner_id=to_owner_id)
            return new_rp_offer
        except Exception as e:
            logging.error(e)
            return False

    def get_offers_from_user(self, user_id):
        try:
            user_offers = self.select().where(self._schema.model.from_owner_id == user_id)
            return user_offers
        except self.DoesNotExist:
            return []

    def get_offers_to_user(self, user_id):
        try:
            user_offers = self.select().where(self._schema.model.to_owner_id == user_id)
            return user_offers
        except self.DoesNotExist:
            return []

    def get_offer_to_profile(self, from_user_id, profile_id):
        try:
            to_user_id = RpProfile().get_profile(profile_id)
            if to_user_id:
                to_user_id = to_user_id.owner_id
                user_offers = self.get((self._schema.model.from_owner_id == from_user_id) &
                                       (self._schema.model.to_owner_id == to_user_id))
                return user_offers
            else:
                return []
        except self.DoesNotExist:
            return []

    def get_offer_from_profile(self, from_profile_id, to_user_id):
        try:
            from_user_id = RpProfile().get_profile(from_profile_id)
            if from_user_id:
                user_offers = self.get((self._schema.model.from_owner_id == from_user_id) &
                                       (self._schema.model.to_owner_id == to_user_id))
                return user_offers
            else:
                return []
        except self.DoesNotExist:
            return []


class BlockedUser(peewee.Model):
    user = peewee.ForeignKeyField(User, on_delete='cascade')
    blocked = peewee.ForeignKeyField(User, on_delete='cascade')

    class Meta:
        database = db
        primary_key = peewee.CompositeKey('user', 'blocked')

    def add(self, user_id, blocked_id):
        try:
            user = User.get(User.id == user_id)
            blocked_user = User.get(User.id == blocked_id)
            added_item = self.create(user=user, blocked=blocked_user)
            return added_item
        except Exception as error_msg:
            logging.error(error_msg)
            return False

    def is_profile_blocked(self, user_id, blocked_profile_id):
        try:
            blocked_id = RpProfile.select(RpProfile.owner_id).where(RpProfile.id == blocked_profile_id)
            item = self.select().where((self._schema.model.user_id == user_id) &
                                       self._schema.model.blocked_id.in_(blocked_id))
            if len(item):
                return True
            else:
                return False
        except self.DoesNotExist:
            return False

    def get_list(self, user_id):
        try:
            item_list = self.select().join(User).where(self._schema.model.user_id == user_id)
            return item_list
        except self.DoesNotExist:
            return []

    def delete_from_list(self, user_id, blocked_id):
        try:
            delete_item = self.delete().where((self._schema.model.user_id == user_id) &
                                              (self._schema.model.blocked_id == blocked_id))
            delete_item.execute()
            return True
        except self.DoesNotExist:
            return False


class AdditionalField(peewee.Model):
    title = peewee.CharField(default='Не указано', unique=True)
    description = peewee.CharField(default='Не указано')

    class Meta:
        database = db

    def create_item(self):
        try:
            new_field = self.create()
            return new_field
        except Exception as error_message:
            logging.error(f'{error_message}')
            return False

    def get_item(self, field_id):
        try:
            field = self.get(self._schema.model.id == field_id)
            return field
        except self.DoesNotExist:
            return []

    def get_item_list(self):
        try:
            fields = self.select()
            return fields
        except self.DoesNotExist:
            return []

    def delete_item(self, field_id):
        try:
            deleteng_field = self.delete().where(self._schema.model.id == field_id)
            deleteng_field.execute()
            return True
        except self.DoesNotExist:
            return False


class ProfileAdditionalField(peewee.Model):
    profile_field = RpProfile
    additional_field = AdditionalField

    profile = peewee.ForeignKeyField(profile_field, on_delete='cascade')
    item = peewee.ForeignKeyField(additional_field, on_delete='cascade')
    is_allowed = peewee.BooleanField(default=True)

    class Meta:
        database = db
        primary_key = peewee.CompositeKey('profile', 'item')

    def add(self, profile_id, item_id):
        try:
            profile = self.profile_field().get_profile(profile_id)
            item = self.additional_field().get_item(item_id)
            added_item = self.create(profile=profile, item=item)
            return added_item
        except Exception as error_msg:
            logging.error(error_msg)
            return False

    def get_list(self, profile_id):
        try:
            item_list = self.select().join(self.additional_field).where(self._schema.model.profile_id == profile_id)
            return item_list
        except self.DoesNotExist:
            return []

    def delete_from_list(self, profile_id, item_id):
        try:
            delete_item = self.delete().where((self._schema.model.profile_id == profile_id) &
                                              (self._schema.model.item_id == item_id))
            delete_item.execute()
            return True
        except self.DoesNotExist:
            return False


class SettingList(AdditionalField):
    pass


class ProfileSettingList(ProfileAdditionalField):
    additional_field = SettingList
    item = peewee.ForeignKeyField(additional_field, on_delete='cascade')


class RpRating(AdditionalField):
    pass


class ProfileRpRatingList(ProfileAdditionalField):
    additional_field = RpRating
    item = peewee.ForeignKeyField(additional_field, on_delete='cascade')


class Gender(AdditionalField):
    pass


class ProfileGenderList(ProfileAdditionalField):
    additional_field = Gender
    item = peewee.ForeignKeyField(additional_field, on_delete='cascade')


class Species(AdditionalField):
    pass


class ProfileSpeciesList(ProfileAdditionalField):
    additional_field = Species
    item = peewee.ForeignKeyField(additional_field, on_delete='cascade')


class OptionalTag(AdditionalField):
    pass


class ProfileOptionalTagList(ProfileAdditionalField):
    additional_field = OptionalTag
    item = peewee.ForeignKeyField(additional_field, on_delete='cascade')


class UserPath(peewee.Model):
    user = peewee.ForeignKeyField(User, on_delete='cascade')
    time = peewee.FloatField()
    menu_id = peewee.CharField()
    menu_args = peewee.CharField()

    class Meta:
        database = db

    def add(self, user_id, create_time):
        try:
            user = User.get(User.id == user_id)
            added_item = self.create(user=user, time=create_time)
            return added_item
        except Exception as error_msg:
            logging.error(error_msg)
            return False

    def get_list(self, user_id):
        try:
            item_list = self.select().join(User).where(self._schema.model.user_id == user_id)
            return item_list
        except self.DoesNotExist:
            return []

    def delete_from_list(self, user_id, blocked_id):
        try:
            delete_item = self.delete().where((self._schema.model.user_id == user_id) &
                                              (self._schema.model.blocked_id == blocked_id))
            delete_item.execute()
            return True
        except self.DoesNotExist:
            return False

    def delete_by_time(self, start_time):
        try:
            delete_item = self.delete().where((self._schema.model.time < start_time))
            delete_item.execute()
            return True
        except self.DoesNotExist:
            return False

    def delete_by_path_id(self, path_id):
        try:
            delete_item = self.delete().where((self._schema.model.id == path_id))
            delete_item.execute()
            return True
        except self.DoesNotExist:
            return False


class AvailableActions(peewee.Model):
    user_id = peewee.IntegerField(primary_key=True)
    actions = peewee.CharField()

    class Meta:
        database = db

    def get_actions(self, user_id):
        try:
            action_list = self.get(self._schema.model.user_id == user_id)
            return action_list
        except self.DoesNotExist:
            action_list = self.create(user_id=user_id, actions='[]')
            return action_list

    def update_actions(self, user_id, action_list):
        user_actions = self.get_actions(user_id)
        user_actions.actions = json.dumps(action_list, ensure_ascii=False)
        user_actions.save()

    def is_action_available(self, user_id, action):
        user_actions = self.get_actions(user_id)
        available_actions = json.loads(user_actions.actions)
        return action in available_actions


class Notification(peewee.Model):
    owner_id = peewee.IntegerField(default=0)
    title = peewee.CharField()
    is_read = peewee.BooleanField(default=False)
    create_time = peewee.IntegerField(default=0)
    description = peewee.CharField(default='')
    attachment = peewee.CharField(default='[]')
    buttons = peewee.CharField(default='[]')

    class Meta:
        database = db

    def create_item(self, owner_id, title):
        new_notification = self.create(owner_id=owner_id, title=title)
        return new_notification

    def get_item_list(self, owner_id, count=8):
        try:
            notifications = self.select()\
                .where(self._schema.model.owner_id == owner_id)\
                .order_by(self._schema.model.create_time.desc())\
                .limit(count)
            return notifications
        except self.DoesNotExist:
            return []

    def get_item(self, notofocation_id):
        try:
            notifications = self.get(self._schema.model.id == notofocation_id)
            return notifications
        except self.DoesNotExist:
            return []

    def delete_item(self, notification_id):
        try:
            deleted_notification = self.delete().where(self._schema.model.id == notification_id)
            deleted_notification.execute()
            return True
        except self.DoesNotExist:
            return False

    def get_new_items(self):
        try:
            notifications = self.select()\
                .where(~self._schema.model.is_read)\
                .order_by(self._schema.model.create_time.desc())\
                .group_by(self._schema.model.owner_id)
            return notifications
        except self.DoesNotExist:
            return []


def suit_by_parameters(profile_id, parameter_list, count, offset):
    try:
        similarity = list()
        unsimilarity = list()

        for parameter in parameter_list:
            allowed = parameter.select(parameter.item_id)\
                .where((parameter.profile_id == profile_id) & parameter.is_allowed)
            not_allowed = parameter.select(parameter.item_id)\
                .where((parameter.profile_id == profile_id) & ~parameter.is_allowed)
            similarity.append(parameter
                              .select()
                              .where(parameter.is_allowed &
                                     parameter.item_id.in_(allowed)))
            unsimilarity.append(parameter
                                .select()
                                .where(parameter.is_allowed &
                                       parameter.item_id.in_(not_allowed)))

        s_union = similarity[0]
        for sim in similarity[1:]:
            s_union += sim
        similarity_count = s_union.select(0 - peewee.fn.COUNT()).where(s_union.c.profile_id == RpProfile.id)
        have_similarity = s_union.select(peewee.fn.COUNT() > 0).where(s_union.c.profile_id == RpProfile.id)

        ns_union = unsimilarity[0]
        for nsim in unsimilarity[1:]:
            ns_union |= nsim
        not_have_similarity = ns_union.select(peewee.fn.COUNT() > 0).where(ns_union.c.profile_id == RpProfile.id)

        user_id = RpProfile.select(RpProfile.owner_id).where(RpProfile.id == profile_id)
        blocked_users = BlockedUser.select(BlockedUser.blocked_id).where(BlockedUser.user_id == user_id)
        actual_time = time.time() - profile_actual_time

        profiles_list = RpProfile\
            .select()\
            .where(peewee.Tuple(True).in_(have_similarity) &
                   peewee.Tuple(False).in_(not_have_similarity) &
                   RpProfile.owner_id.not_in(user_id) &
                   ~RpProfile.search_preset &
                   (RpProfile.create_date > actual_time) &
                   RpProfile.owner_id.not_in(blocked_users))\
            .order_by(similarity_count, RpProfile.create_date.desc())\
            .limit(count).offset(offset)
        # print('\n\nprofiles_list\n', profiles_list.dicts())
        # profiles_list = list(profiles_list)
        return profiles_list
    except RpProfile.DoesNotExist:
        return []


def find_suitable_profiles(profile_id, count, offset):
    parameters = (
        ProfileGenderList,
        ProfileSettingList,
        ProfileSpeciesList,
        ProfileRpRatingList,
        ProfileOptionalTagList
    )
    suit_profiles = suit_by_parameters(profile_id, parameters, count, offset)
    return suit_profiles


def init_db():
    User.create_table()
    RpProfile.create_table()
    RoleOffer.create_table()
    SettingList.create_table()
    ProfileSettingList.create_table()
    Notification.create_table()
    RpRating.create_table()
    ProfileRpRatingList.create_table()
    Gender.create_table()
    ProfileGenderList.create_table()
    Species.create_table()
    ProfileSpeciesList.create_table()
    AvailableActions.create_table()
    OptionalTag.create_table()
    ProfileOptionalTagList.create_table()
    BlockedUser.create_table()
    UserPath.create_table()


def update_admins(admin_list):
    for admin in admin_list:
        if admin['role'] in ['creator', 'administrator']:
            user = User().get_user(admin['id'])
            if user:
                user.is_admin = True
                user.save()


def update_db():
    import playhouse.migrate as playhouse_migrate

    db_migrate = peewee.SqliteDatabase(db_filename, pragmas={'journal_mode': 'wal',
                                                             'cache_size': 64,
                                                             'foreign_keys': 0,
                                                             'ignore_check_constraints': 0,
                                                             'synchronous': 0})
    migrator = playhouse_migrate.SqliteMigrator(db_migrate)
    try:
        playhouse_migrate.migrate(
            migrator.add_column('RpProfile', 'show_link', peewee.BooleanField(default=0)),
        )
    except Exception as e:
        print(e)

    #         playhouse_migrate.migrate(
    #             migrator.add_column('RpProfile', 'show_link', RpProfile.show_link),
    #             # migrator.rename_column('ProfileSettingList', 'item_id', 'item'),
    #             # migrator.drop_column('RoleOffer', 'to_profile_id')
    #         )


if __name__ == "__main__":
    # logging.basicConfig(format='%(filename)-15s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
    #                     level=logging.INFO)
    # TestField.create_table()
    # for i in range(2):
    #     af = TestField().create_field()
    #     af.title = f'test field {i}'
    #     af.save()
    # t_f = TestField().get_field_list()
    # for t in t_f:
    #     print(f'{t.id} - {t.title}')
    # t_id = int(input('delete id'))
    # print(TestField().delete_field(t_id))
    update_db()
    pass
