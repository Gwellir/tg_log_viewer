from django.core.paginator import Paginator
from django.utils.functional import cached_property


class UserPaginator(Paginator):

    @cached_property
    def count(self):
        return self.object_list.model.objects.last().id

    def page(self, number):
        """Return a Page object for the given 1-based page number."""
        number = self.validate_number(number)
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        if top + self.orphans >= self.count:
            top = self.count
        return self._get_page(self.object_list.filter(id__gte=bottom, id__lt=top), number, self)
