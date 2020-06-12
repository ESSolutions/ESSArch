from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from mptt.templatetags.mptt_tags import cache_tree_children

register = template.Library()


class RecurseTreeNode(template.Node):
    def __init__(self, template_nodes, queryset_var, nodevar, childrenvar):
        self.template_nodes = template_nodes
        self.queryset_var = queryset_var
        self.nodevar = nodevar
        self.childrenvar = childrenvar

    def _render_node(self, context, node):
        bits = []
        context.push()
        for child in node.get_children():
            bits.append(self._render_node(context, child))
        context[self.nodevar] = node
        context[self.childrenvar] = mark_safe(''.join(bits))
        rendered = self.template_nodes.render(context)
        context.pop()
        return rendered

    def render(self, context):
        queryset = self.queryset_var.resolve(context)
        roots = cache_tree_children(queryset)
        bits = [self._render_node(context, node) for node in roots]
        return ''.join(bits)


@register.tag
def recursetree(parser, token):

    bits = token.contents.split()
    if len(bits) != 4:
        raise template.TemplateSyntaxError(_('%s tag requires a queryset') % bits[0])
    queryset_var = template.Variable(bits[1])
    nodevar = bits[2]
    childrenvar = bits[3]

    template_nodes = parser.parse(('endrecursetree',))
    parser.delete_first_token()

    return RecurseTreeNode(template_nodes, queryset_var, nodevar, childrenvar)
