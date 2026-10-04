define(["require", "exports", "common/components/DataStoreComponent", "common/lib/classnames", "common/lib/preact", "common/util/CSSUtil", "project/data/GameTypes"], function (require, exports, DataStoreComponent, classnames_1, preact, CSSUtil_1, GameTypes_1) {
    "use strict";
    // Reg2026 : la case DRS du bandeau pilote est remplacée par deux cases STRAIGHT / OVERTAKE,
    // dessinées avec les mêmes classes que la case DRS d'origine (DRSDisplay.css).
    //
    // Tout est déduit de CarData.DRSState (que le mod UE4SS Reg2026 force à Active dans les zones) :
    //   STRAIGHT : allumée quand l'état est Active (voiture dans une zone Straight Mode).
    //   OVERTAKE : « disponible » (atténuée) quand le jeu a accordé le DRS (Detected / Enabled, moins d'1 s
    //              au point de détection), allumée si la voiture entre dans la zone avec ce droit.
    Object.defineProperty(exports, "__esModule", { value: true });
    exports.DRSDisplay = void 0;
    (0, CSSUtil_1.loadCSS)('project/components/raceWeekend/DRSDisplay');
    (0, CSSUtil_1.loadCSS)('project/components/raceWeekend/Reg2026Modes');
    const EDRSState = GameTypes_1.EDRSState;
    function ModeBox(props) {
        const modifiers = (0, classnames_1.classNames)(props.mode, props.state, props.state == 'active' ? 'active' : 'inactive', { focused: props.focused });
        return preact.h("div", { className: (0, classnames_1.classNames)('DRSDisplay_root Reg2026Mode_root', modifiers) },
            preact.h("div", { className: (0, classnames_1.classNames)('DRSDisplay_border Reg2026Mode_border', modifiers) }),
            preact.h("div", { className: (0, classnames_1.classNames)('DRSDisplay_label Reg2026Mode_label', modifiers) }, props.label));
    }
    class _DRSDisplay extends preact.Component {
        state = { straight: false, overtake: 'off' };
        _last = EDRSState.Disabled;
        _overtakeInZone = false;
        onContextChanged(context, dataHelper) {
            dataHelper.addPropertyListener(context, 'DRSState', this.onDRSStateChanged);
            dataHelper.getAllPropertiesNow();
        }
        render(props, state) {
            return (!props.disabled &&
                preact.h("div", { className: 'Reg2026Modes_root' },
                    preact.h(ModeBox, { mode: 'straight', label: 'STRAIGHT', state: state.straight ? 'active' : 'off', focused: props.focused }),
                    preact.h(ModeBox, { mode: 'overtake', label: 'OVERTAKE', state: state.overtake, focused: props.focused })));
        }
        onDRSStateChanged = (value) => {
            const drs = value;
            const prev = this._last;
            this._last = drs;
            if (drs == EDRSState.Active) {
                // droit au dépassement acquis à l'entrée de zone, conservé jusqu'à la sortie
                if (prev == EDRSState.Detected || prev == EDRSState.Enabled)
                    this._overtakeInZone = true;
            }
            else {
                this._overtakeInZone = false;
            }
            let overtake = 'off';
            if (drs == EDRSState.Active && this._overtakeInZone)
                overtake = 'active';
            else if (drs == EDRSState.Detected || drs == EDRSState.Enabled)
                overtake = 'available';
            this.setState({ straight: drs == EDRSState.Active, overtake });
        };
    }
    exports.DRSDisplay = DataStoreComponent.decorate(_DRSDisplay);
});
