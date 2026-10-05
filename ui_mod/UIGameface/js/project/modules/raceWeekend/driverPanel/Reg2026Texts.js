define(["require", "exports", "common/core/Localisation"], function (require, exports, Localisation) {
    "use strict";
    // Reg2026 : noms et descriptions des stratégies ERS au règlement 2026. Les comportements sont dans
    // Reg2026Patch.dll (stratégie de la voiture en +0xEF2) :
    //   Déploiement -> BOOST (comportement du jeu, stratégie de course par défaut de l'IA)
    //   Neutre      -> ÉQUILIBRÉ (comportement du jeu)
    //   Top-Up      -> RÉSERVE : pas de déploiement sauf Overtake Mode ou défense (voiture à moins d'1 s derrière)
    //   Récupération -> LIFT & COAST : plus d'électrique au-delà de 250 km/h, recharge au-dessus
    // Toutes les vues passent par Localisation.translate au moment de l'appel : on l'enveloppe une seule fois.
    Object.defineProperty(exports, "__esModule", { value: true });
    const TEXTS = {
        fr: {
            '[ERS_DEPLOY]': 'Boost',
            '[ERS_NEUTRAL]': 'Équilibré',
            '[CAR_SETUP_ERS_TOP_UP]': 'Réserve',
            '[ERS_HARVEST]': 'Lift & Coast',
            '[CAR_SETUP_ERS_DESCR_RACE_DEPLOY]': "Le pilote déploie à fond en accélération pour gagner du temps au tour, tant que la batterie est au-dessus de 40 %. Elle se recharge au freinage et en bout de ligne droite. C'est la stratégie de course de l'IA.",
            '[CAR_SETUP_ERS_DESCR_NEUTRAL]': "Gestion équilibrée de l'énergie : le pilote déploie à fond en accélération seulement au-dessus de 60 % de batterie, et garde le reste.",
            '[CAR_SETUP_ERS_DESCR_RACE_TOP_UP]': "Le pilote recharge et garde son énergie. Il ne déploie à fond qu'en bataille, avec une voiture à moins d'1 s devant ou derrière, et en Overtake Mode.",
            '[CAR_SETUP_ERS_DESCR_RACE_HARVEST]': "Le pilote lève le pied en bout de ligne droite : plus d'électrique au-delà de 250 km/h et récupération à fond au-dessus. Plus lent, mais la batterie se remplit.",
        },
        en: {
            '[ERS_DEPLOY]': 'Boost',
            '[ERS_NEUTRAL]': 'Balanced',
            '[CAR_SETUP_ERS_TOP_UP]': 'Reserve',
            '[ERS_HARVEST]': 'Lift & Coast',
            '[CAR_SETUP_ERS_DESCR_RACE_DEPLOY]': 'The driver deploys at full power when accelerating to gain lap time, as long as the battery is above 40 %. It charges under braking and at the end of the straights. This is the AI race strategy.',
            '[CAR_SETUP_ERS_DESCR_NEUTRAL]': 'Balanced energy management: the driver deploys at full power when accelerating only above 60 % battery, and keeps the rest.',
            '[CAR_SETUP_ERS_DESCR_RACE_TOP_UP]': 'The driver charges and keeps the energy. Full deployment only in a battle, with a car within 1 s ahead or behind, and in Overtake Mode.',
            '[CAR_SETUP_ERS_DESCR_RACE_HARVEST]': 'The driver lifts at the end of the straights: no electrical power above 250 km/h and full harvesting above it. Slower, but the battery fills up.',
        },
    };
    const original = Localisation.translate;
    if (!original.__reg2026) {
        let texts;
        const wrapped = function (str) {
            if (texts === undefined) {
                // langue du jeu, d'après le texte d'origine d'une clé connue
                let neutral = '';
                try {
                    neutral = String(original('[ERS_NEUTRAL]'));
                }
                catch (e) {
                    neutral = '';
                }
                if (!neutral || neutral.charAt(0) == '[' || neutral.charAt(0) == '!')
                    return original(str);  // traductions pas encore chargées : on réessaiera
                texts = /^neutre/i.test(neutral) ? TEXTS.fr : TEXTS.en;
            }
            if (typeof str === 'string' && Object.prototype.hasOwnProperty.call(texts, str))
                return texts[str];
            return original(str);
        };
        wrapped.__reg2026 = true;
        Localisation.translate = wrapped;
    }
});
