class DatabaseRouter:
    """
    Điều hướng app SANPHAM sử dụng database sanpham.
    Các app còn lại sử dụng database default.
    """

    sanpham_apps = {"SANPHAM"}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.sanpham_apps:
            return "sanpham"
        return "default"

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.sanpham_apps:
            return "sanpham"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        db_set = {"default", "sanpham"}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return obj1._state.db == obj2._state.db
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.sanpham_apps:
            return db == "sanpham"
        return db == "default"