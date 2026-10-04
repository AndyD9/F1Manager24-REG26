define(["require", "exports", "common/components/DataStoreComponent", "common/lib/classnames", "common/lib/preact", "common/util/CSSUtil", "project/data/GameTypes"], function (require, exports, DataStoreComponent, classnames_1, preact, CSSUtil_1, GameTypes_1) {
    "use strict";
    // Reg2026 : la case DRS du bandeau pilote est remplacée par deux cases STRAIGHT / OVERTAKE,
    // dessinées avec les mêmes classes que la case DRS d'origine (DRSDisplay.css).
    //
    //   STRAIGHT : aileron ouvert par la simulation (DRSState = Active). Avec Reg2026Patch.dll, toute la
    //              grille l'a dans les zones Straight Mode.
    //   OVERTAKE : la DLL donne +12,5 % de batterie aux voitures à moins d'1 s au point de détection.
    //              La batterie ne gagne normalement que quelques % par seconde : un saut d'au moins
    //              OVERTAKE_JUMP points signale le bonus. La case reste allumée jusqu'à la fin du tour,
    //              et au moins OVERTAKE_MIN_MS.
    Object.defineProperty(exports, "__esModule", { value: true });
    exports.DRSDisplay = void 0;
    (0, CSSUtil_1.loadCSS)('project/components/raceWeekend/DRSDisplay');
    (0, CSSUtil_1.loadCSS)('project/components/raceWeekend/Reg2026Modes');
    const EDRSState = GameTypes_1.EDRSState;
    const OVERTAKE_JUMP = 8;
    const OVERTAKE_MIN_MS = 20000;
    function ModeBox(props) {
        const modifiers = (0, classnames_1.classNames)(props.mode, props.active ? 'active' : 'inactive', { focused: props.focused });
        return preact.h("div", { className: (0, classnames_1.classNames)('DRSDisplay_root Reg2026Mode_root', modifiers) },
            preact.h("div", { className: (0, classnames_1.classNames)('DRSDisplay_border Reg2026Mode_border', modifiers) }),
            preact.h("div", { className: (0, classnames_1.classNames)('DRSDisplay_label Reg2026Mode_label', modifiers) }, props.label));
    }
    class _DRSDisplay extends preact.Component {
        state = { straight: false, overtake: false };
        _battery = undefined;
        _lap = 0;
        _overtakeLap = -1;
        _overtakeAt = 0;
        _timer = undefined;
        onContextChanged(context, dataHelper) {
            dataHelper.addPropertyListener(context, 'DRSState', this.onDRSStateChanged);
            dataHelper.addPropertyListener(context, 'batteryPercentage', this.onBatteryChanged);
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
        refreshOvertake = () => {
            const recent = Date.now() - this._overtakeAt < OVERTAKE_MIN_MS;
            const overtake = this._overtakeLap >= 0 && (this._lap === this._overtakeLap || recent);
            if (overtake !== this.state.overtake)
                this.setState({ overtake });
        };
        onDRSStateChanged = (value) => {
            this.setState({ straight: value == EDRSState.Active });
        };
        onBatteryChanged = (value) => {
            const battery = Number(value);
            if (this._battery !== undefined && battery - this._battery >= OVERTAKE_JUMP) {
                this._overtakeLap = this._lap;
                this._overtakeAt = Date.now();
                clearTimeout(this._timer);
                this._timer = setTimeout(this.refreshOvertake, OVERTAKE_MIN_MS + 100);
            }
            this._battery = battery;
            this.refreshOvertake();
        };
        onLapChanged = (value) => {
            this._lap = Number(value);
            this.refreshOvertake();
        };
    }
    exports.DRSDisplay = DataStoreComponent.decorate(_DRSDisplay);
});
