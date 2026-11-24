# grammar-engine - Argentine Spanish: everything of Spanish, plus the voseo.
# A variant derives from its language and only adds or replaces what differs. To switch an inherited rule off, list it in removed_rules.
# SPDX-License-Identifier: MIT

from . import es
from ..core import rule

# "vos tienes" mixes the pronoun of the voseo with the verb of the tuteo
VOSEO_VERBS = {
    'tienes': 'tenés', 'eres': 'sos', 'puedes': 'podés', 'quieres': 'querés', 'haces': 'hacés', 'vienes': 'venís', 'dices': 'decís', 'sabes': 'sabés', 'pides': 'pedís',
    'piensas': 'pensás', 'comes': 'comés', 'hablas': 'hablás', 'duermes': 'dormís', 'sientes': 'sentís', 'tomas': 'tomás', 'trabajas': 'trabajás', 'vives': 'vivís',
    'escribes': 'escribís', 'conoces': 'conocés', 'pones': 'ponés', 'sales': 'salís', 'necesitas': 'necesitás', 'miras': 'mirás', 'llamas': 'llamás', 'ves': 'ves',
    'cantas': 'cantás', 'bailas': 'bailás', 'estudias': 'estudiás', 'juegas': 'jugás', 'recuerdas': 'acordás', 'tienes': 'tenés', 'dejas': 'dejás', 'llevas': 'llevás',
}
# "vos tienes" mixes the pronoun of the voseo with the verb of the tuteo; the verb which is the same in both ("vos ves") is left out
VOSEO = [('vos %s' % tuteo, 'vos %s' % voseo, False) for tuteo, voseo in VOSEO_VERBS.items() if tuteo != voseo]


class Grammar(es.Grammar):
    """Argentine Spanish: the Spanish grammar, plus the verb forms of the voseo."""
    language = 'es_ar'

    messages = {
        'en': {'es_ar.voseo': 'In Argentine Spanish the verb of "vos" is: "{arg}".'},
        'fr': {'es_ar.voseo': 'En espagnol argentin, le verbe de « vos » est : « {arg} ».'},
        'es': {'es_ar.voseo': 'En el español rioplatense el verbo de "vos" es: "{arg}".'},
    }

    @rule('es_ar.voseo', 'agreement', 0.8)
    def voseo(self, p):
        """vos tienes -> vos tenés"""
        self.phrases(p, VOSEO, 'es_ar.voseo')
