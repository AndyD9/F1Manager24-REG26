define(["require", "exports", "common/components/DataStoreComponent", "common/core/DataStore", "common/lib/classnames", "common/lib/preact", "common/util/CSSUtil", "project/data/GameTypes"], function (require, exports, DataStoreComponent, DS, classnames_1, preact, CSSUtil_1, GameTypes_1) {
    "use strict";
    // Reg2026 : la case DRS du bandeau pilote est remplacée par deux cases STRAIGHT / OVERTAKE,
    // dessinées avec les mêmes classes que la case DRS d'origine (DRSDisplay.css).
    //
    //   STRAIGHT : aileron ouvert par la simulation (DRSState = Active). Avec Reg2026Patch.dll, toute la
    //              grille l'a dans les zones Straight Mode.
    //   OVERTAKE : règle 2026 appliquée à l'affichage : à moins d'1 s de la voiture devant au passage de
    //              la ligne, la case reste allumée pendant le tour qui commence. L'écart est lu dans le
    //              classement (timeDeltaFromLead), un peu après le changement de tour pour qu'il soit à jour.
    //              Le saut de batterie ne suffit pas : la recharge au freinage fait des sauts aussi grands.
    Object.defineProperty(exports, "__esModule", { value: true });
    exports.DRSDisplay = void 0;
    (0, CSSUtil_1.loadCSS)('project/components/raceWeekend/DRSDisplay');
    (0, CSSUtil_1.loadCSS)('project/components/raceWeekend/Reg2026Modes');
    const EDRSState = GameTypes_1.EDRSState;
    const STANDINGS = ['RaceSim', 'RaceStandings'];
    const OVERTAKE_GAP = 1.0;
    const CHECK_DELAY_MS = 1500;
    const MAX_DRIVER_ID = 64;
    function ModeBox(props) {
        const modifiers = (0, classnames_1.classNames)(props.mode, props.active ? 'active' : 'inactive', { focused: props.focused });
        return preact.h("div", { className: (0, classnames_1.classNames)('DRSDisplay_root Reg2026Mode_root', modifiers) },
            preact.h("div", { className: (0, classnames_1.classNames)('DRSDisplay_border Reg2026Mode_border', modifiers) }),
            preact.h("div", { className: (0, classnames_1.classNames)('DRSDisplay_label Reg2026Mode_label', modifiers) }, props.label));
    }
    function standing(driverID, prop) {
        try {
            return DS.getValue([...STANDINGS, driverID + ''], prop);
        }
        catch (e) {
            return undefined;
        }
    }
    /// écart en secondes avec la voiture devant, ou undefined (en tête, données absentes)
    function gapToCarAhead(driverID) {
        const pos = Number(standing(driverID, 'racePosition'));
        const delta = Number(standing(driverID, 'timeDeltaFromLead'));
        if (!(pos > 1) || isNaN(delta))
            return undefined;
        for (let id = 0; id < MAX_DRIVER_ID; id++) {
            if (Number(standing(id, 'racePosition')) !== pos - 1)
                continue;
            const ahead = Number(standing(id, 'timeDeltaFromLead'));
            return isNaN(ahead) ? undefined : delta - ahead;
        }
        return undefined;
    }
    class _DRSDisplay extends preact.Component {
        state = { straight: false, overtake: false };
        _context = undefined;
        _lap = undefined;
        _timer = undefined;
        onContextChanged(context, dataHelper) {
            this._context = context;
            this._lap = undefined;
            dataHelper.addPropertyListener(context, 'DRSState', this.onDRSStateChanged);
            dataHelper.addPropertyListener(context, 'lapCount', this.onLapChanged);
            dataHelper.getAllPropertiesNow();
        }
        componentWillUnmount() {
            clearTimeout(this._timer);
        }
        render(props, state) {
            return (!props.disabled &&
                preact.h("div", { className: 'Reg2026Modes_root' },
                    preact.h(ModeBox, { mode: 'straight', label: 'STRAIGHT', active: state.straight, focused: props.focused }),
                    preact.h(ModeBox, { mode: 'overtake', label: 'OVERTAKE', active: state.overtake, focused: props.focused })));
        }
        checkOvertake = () => {
            let overtake = false;
            try {
                const driverID = DS.getValue(this._context, 'driverIndex');
                const gap = gapToCarAhead(driverID);
                overtake = gap !== undefined && gap > 0 && gap <= OVERTAKE_GAP;
            }
            catch (e) {
                overtake = false;
            }
            if (overtake !== this.state.overtake)
                this.setState({ overtake });
        };
        onDRSStateChanged = (value) => {
            this.setState({ straight: value == EDRSState.Active });
        };
        onLapChanged = (value) => {
            const lap = Number(value);
            const crossedLine = this._lap !== undefined && lap > this._lap && lap > 1;
            this._lap = lap;
            clearTimeout(this._timer);
            if (crossedLine) {
                this._timer = setTimeout(this.checkOvertake, CHECK_DELAY_MS);
            }
            else if (this.state.overtake) {
                this.setState({ overtake: false });
            }
        };
    }
    exports.DRSDisplay = DataStoreComponent.decorate(_DRSDisplay);
});
