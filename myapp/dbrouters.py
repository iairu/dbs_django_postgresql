# Citame z dota2 remote PostgreSQL ale zapisujeme len lokalne
# Potrebne pre spravne smerovanie poziadaviek z modelov
class MyDBRouter(object):

    def db_for_read(self, model, **hints):
        """ reading SomeModel from otherdb """
        return 'readonly'

    def db_for_write(self, model, **hints):
        """ writing SomeModel to otherdb """
        return 'default'
        