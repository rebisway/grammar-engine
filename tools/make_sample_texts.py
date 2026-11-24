"""Writes the sample texts of examples/sample_texts/ from one list of (wrong, right) sentences per language.

    python tools/make_sample_texts.py

For each language it writes four files:
    <lang>_errors.md       the sentences with their mistakes, in sections (one section per kind of mistake)
    <lang>_errors.txt     the same sentences as plain text, one paragraph per line
    <lang>_corrected.md   the corrected sentences, same layout
    <lang>_corrected.txt  the corrected sentences, same layout

The mistakes are the ones the engine looks for; tests/test_samples.py checks that every file of errors gets the problems
which are announced here (the rules after each sentence) and that the corrected files get none. A sentence is
(wrong, right, [rules which must flag the wrong one]); a sentence with no rule is a decoy: correct, but close to a mistake.
Two French rules (fr.participle, fr.infinitive) need the spelling dictionary of the host; the tests give the engine a `known` function
which accepts every word.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'examples', 'sample_texts')

SAMPLES = {
    'fr': {
        'title': ("Texte d'essai : erreurs de français", "Texte d'essai : le même texte corrigé"),
        'sections': [
            ('Accords du groupe nominal', [
                ('Les enfant jouent dans le jardin.', 'Les enfants jouent dans le jardin.', ['fr.det_number']),
                ('Les pomme sont mûres.', 'Les pommes sont mûres.', ['fr.det_number']),
                ('Une grand maison se dresse au bout du chemin.', 'Une grande maison se dresse au bout du chemin.', ['fr.noun_adjective']),
                ('Des petit chemins mènent à la rivière.', 'De petits chemins mènent à la rivière.', ['fr.noun_adjective']),
                ('Le voiture est garée devant la porte.', 'La voiture est garée devant la porte.', ['fr.det_gender']),
                ('Chaque jours, le facteur passe à midi.', 'Chaque jour, le facteur passe à midi.', ['fr.det_number']),
                ('Ma amie habite à côté.', 'Mon amie habite à côté.', ['fr.possessive_vowel']),
                ('Tout les matins, elle ouvre la fenêtre.', 'Tous les matins, elle ouvre la fenêtre.', ['fr.tout']),
                ('Elle a des cheveux noirs et une robe bleu ciel.', 'Elle a des cheveux noirs et une robe bleu ciel.', []),
            ]),
            ('Accords du verbe', [
                ('Les chats dort sur le lit.', 'Les chats dorment sur le lit.', ['fr.subject_noun_verb']),
                ('Tu mange trop vite.', 'Tu manges trop vite.', ['fr.subject_verb']),
                ('Nous mange à midi.', 'Nous mangeons à midi.', ['fr.subject_verb']),
                ('Elle est grand pour son âge.', 'Elle est grande pour son âge.', ['fr.attribute']),
                ('Les filles sont content de partir.', 'Les filles sont contentes de partir.', ['fr.attribute']),
                ('Je a faim depuis ce matin.', "J'ai faim depuis ce matin.", ['fr.verb_person']),
                ("C'est moi qui a préparé le dîner.", "C'est moi qui ai préparé le dîner.", ['fr.relative_person']),
                ('La plupart des gens est déjà parti.', 'La plupart des gens sont déjà partis.', ['fr.plupart']),
                ('Quelque personnes sont arrivées en retard.', 'Quelques personnes sont arrivées en retard.', ['fr.quelque']),
                ('Il y a deux cent personnes dans la salle.', 'Il y a deux cents personnes dans la salle.', ['fr.number_word']),
            ]),
            ('Participes passés', [
                ('Elle est parti hier soir.', 'Elle est partie hier soir.', ['fr.participle_subject']),
                ('Nous sommes arrivé tard.', 'Nous sommes arrivés tard.', ['fr.participle_subject']),
                ("Elle s'est lavé hier.", "Elle s'est lavée hier.", ['fr.participle_subject']),
                ("Les pommes que j'ai mangé étaient bonnes.", "Les pommes que j'ai mangées étaient bonnes.", ['fr.participle_object']),
                ('Je les ai mangé hier.', 'Je les ai mangés hier.', ['fr.participle_object']),
                ('Elle a mangées la tarte.', 'Elle a mangé la tarte.', ['fr.participle_invariable']),
                ('Il a manger toute la tarte.', 'Il a mangé toute la tarte.', ['fr.participle']),
                ('Il faut mangé avant de partir.', 'Il faut manger avant de partir.', ['fr.infinitive']),
            ]),
            ('Homophones', [
                ('Il ce lave les mains.', 'Il se lave les mains.', ['fr.ce_se']),
                ('Il va a la plage chaque été.', 'Il va à la plage chaque été.', ['fr.a_accent']),
                ('Le village ou il habite est calme.', 'Le village où il habite est calme.', ['fr.ou_where']),
                ('Leur amis sont arrivés.', 'Leurs amis sont arrivés.', ['fr.leur']),
                ("Il c'est trompé de route.", "Il s'est trompé de route.", ['fr.cest_sest']),
                ('Il et parti sans rien dire.', 'Il est parti sans rien dire.', ['fr.et_est']),
                ('Il peu venir demain.', 'Il peut venir demain.', ['fr.peu_peut']),
                ('Il ma dit que sa va mieux.', "Il m'a dit que ça va mieux.", ['fr.ma_ma', 'fr.sa_ca']),
                ('Il à froid.', 'Il a froid.', ['fr.a']),
                ('Ils on peur et ils son partis.', 'Ils ont peur et ils sont partis.', ['fr.ont', 'fr.sont']),
            ]),
            ('Temps et modes', [
                ("Si j'aurais su, je serais venu.", "Si j'avais su, je serais venu.", ['fr.si_tense']),
                ('Il faut que tu viens demain.', 'Il faut que tu viennes demain.', ['fr.subjunctive']),
                ("Bien qu'il a mangé, il a encore faim.", "Bien qu'il ait mangé, il a encore faim.", ['fr.subjunctive']),
                ("Après qu'il soit parti, la maison est restée vide.", "Après qu'il est parti, la maison est restée vide.", ['fr.indicative_after']),
                ('Je ne sais pas si tu viendras.', 'Je ne sais pas si tu viendras.', []),
            ]),
            ('Prépositions et expressions', [
                ('Il essaie à comprendre la règle.', 'Il essaie de comprendre la règle.', ['fr.preposition']),
                ('Il apprend de lire en classe.', 'Il apprend à lire en classe.', ['fr.preposition']),
                ('Ils vont pallier à la pénurie.', 'Ils vont pallier la pénurie.', ['fr.preposition']),
                ('Ce plan est différent que le premier.', 'Ce plan est différent du premier.', ['fr.preposition']),
                ('Malgré que tu viennes, il reste fâché.', 'Bien que tu viennes, il reste fâché.', ['fr.phrase']),
                ('Au dessus de la table, une lampe brille.', 'Au-dessus de la table, une lampe brille.', ['fr.phrase']),
            ]),
            ('Élisions, répétitions et majuscules', [
                ('Si il pleut, nous resterons à la maison.', "S'il pleut, nous resterons à la maison.", ['fr.elision']),
                ('Je pense que il viendra.', "Je pense qu'il viendra.", ['fr.elision']),
                ('Je ai faim depuis ce matin.', "J'ai faim depuis ce matin.", ['fr.elision']),
                ('Le chat et et le chien dorment.', 'Le chat et le chien dorment.', ['any.repeat']),
                ('Il dort. le soleil se lève.', 'Il dort. Le soleil se lève.', ['any.capital']),
            ]),
        ],
    },
    'en': {
        'title': ('Sample text: mistakes in English', 'Sample text: the same text, corrected'),
        'sections': [
            ('Subject and verb', [
                ('He go to school every day.', 'He goes to school every day.', ['en.subject_verb']),
                ('They goes home early.', 'They go home early.', ['en.subject_verb']),
                ('I is happy today.', 'I am happy today.', ['en.subject_verb']),
                ('We was late again.', 'We were late again.', ['en.subject_verb']),
                ("He don't know the answer.", "He doesn't know the answer.", ['en.subject_verb']),
                ('The dogs runs in the park.', 'The dogs run in the park.', ['en.noun_verb']),
                ('Everyone are ready.', 'Everyone is ready.', ['en.everyone']),
                ('There is many people outside.', 'There are many people outside.', ['en.there_is']),
                ('He can go home now.', 'He can go home now.', []),
            ]),
            ('Determiners and nouns', [
                ('A books are on the table.', 'A book is on the table.', ['en.det_number']),
                ('These book is old.', 'These books are old.', ['en.det_number']),
                ('She ate a apple.', 'She ate an apple.', ['en.a_an']),
                ('He is an dog lover.', 'He is a dog lover.', ['en.a_an']),
                ('This information is useful.', 'This information is useful.', []),
            ]),
            ('Verb forms', [
                ('I have went home.', 'I have gone home.', ['en.participle']),
                ('She has ate lunch already.', 'She has eaten lunch already.', ['en.participle']),
                ('I seen him yesterday.', 'I saw him yesterday.', ['en.past']),
                ('If I would have known, I would have come.', 'If I had known, I would have come.', ['en.if_would']),
                ('I have read the book twice.', 'I have read the book twice.', []),
            ]),
            ('Spelling of look-alike words', [
                ('It is better then nothing.', 'It is better than nothing.', ['en.then_than']),
                ('The box is to big for the shelf.', 'The box is too big for the shelf.', ['en.to_too']),
                ('You will loose the game.', 'You will lose the game.', ['en.loose_lose']),
                ('I dont know what to say.', "I don't know what to say.", ['en.phrase']),
                ('You should of called me.', 'You should have called me.', ['en.phrase']),
                ('Its a beautiful day.', "It's a beautiful day.", ['en.phrase']),
            ]),
            ('Capitals and repetitions', [
                ('Yesterday i went to the market.', 'Yesterday I went to the market.', ['en.i']),
                ('The cat sat on the the mat.', 'The cat sat on the mat.', ['any.repeat']),
                ('It rained all day. the streets were empty.', 'It rained all day. The streets were empty.', ['any.capital']),
            ]),
        ],
    },
    'es': {
        'title': ('Texto de prueba: errores en español', 'Texto de prueba: el mismo texto corregido'),
        'sections': [
            ('Concordancia', [
                ('Los casa son grandes.', 'Las casas son grandes.', ['es.det_number']),
                ('La libros están aquí.', 'Los libros están aquí.', ['es.det_number']),
                ('La casa blanco es bonita.', 'La casa blanca es bonita.', ['es.noun_adjective']),
                ('Los libros viejo están en la mesa.', 'Los libros viejos están en la mesa.', ['es.noun_adjective']),
                ('Yo comes pan.', 'Yo como pan.', ['es.subject_verb']),
                ('Nosotros come en casa.', 'Nosotros comemos en casa.', ['es.subject_verb']),
                ('Los niños juega en el parque.', 'Los niños juegan en el parque.', ['es.noun_verb']),
                ('El agua fría es buena.', 'El agua fría es buena.', []),
            ]),
            ('Verbos', [
                ('He comprados los libros.', 'He comprado los libros.', ['es.haber_participle']),
                ('Habían muchas personas en la plaza.', 'Había muchas personas en la plaza.', ['es.impersonal']),
                ('Quiero que vienes mañana.', 'Quiero que vengas mañana.', ['es.subjunctive']),
            ]),
            ('Tildes y palabras parecidas', [
                ('Tu eres muy amable.', 'Tú eres muy amable.', ['es.tilde']),
                ('Cómo estás?', '¿Cómo estás?', ['es.inverted']),
                ('La informacion llegó ayer.', 'La información llegó ayer.', ['es.accent']),
                ('¿Donde vives ahora?', '¿Dónde vives ahora?', ['es.interrogative']),
                ('Pienso de que vendrá.', 'Pienso que vendrá.', ['es.dequeismo']),
                ('Voy a haber si está en casa.', 'Voy a ver si está en casa.', ['es.phrase']),
                ('He echo los deberes.', 'He hecho los deberes.', ['es.haber_echo']),
                ('Mas o menos, todo salió bien.', 'Más o menos, todo salió bien.', ['es.phrase']),
            ]),
            ('Mayúsculas y repeticiones', [
                ('Salimos de casa. el sol brillaba.', 'Salimos de casa. El sol brillaba.', ['any.capital']),
                ('Ladra el el perro.', 'Ladra el perro.', ['any.repeat']),
            ]),
        ],
    },
}


def write(path, text):
    """Writes a UTF-8 file with Unix line ends."""
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def main():
    os.makedirs(OUT, exist_ok=True)
    expected = {}
    for lang, data in SAMPLES.items():
        for index, kind in ((0, 'errors'), (1, 'corrected')):
            md = ['# ' + data['title'][index], '']
            txt = []
            for heading, sentences in data['sections']:
                md += ['## ' + heading, '']
                # one paragraph per section for the markdown, one per sentence for the text file
                md.append(' '.join(s[index] for s in sentences))
                md.append('')
                txt += [s[index] for s in sentences]
            write(os.path.join(OUT, '%s_%s.md' % (lang, kind)), '\n'.join(md))
            write(os.path.join(OUT, '%s_%s.txt' % (lang, kind)), '\n'.join(txt) + '\n')
        expected[lang] = sorted({rule for _, sentences in data['sections'] for s in sentences for rule in s[2]})
    # the rules which every file of errors must trigger, one list per language
    lines = ['# Rules which the files <lang>_errors.* must trigger (written by tools/make_sample_texts.py)']
    for lang in expected:
        lines.append('%s: %s' % (lang, ' '.join(expected[lang])))
    write(os.path.join(OUT, 'expected_rules.txt'), '\n'.join(lines) + '\n')
    print('written to', os.path.normpath(OUT))


if __name__ == '__main__':
    main()
