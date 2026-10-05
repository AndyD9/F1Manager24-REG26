define(["require", "exports", "common/components/DataStoreComponent", "common/core/DataStore", "project/modules/raceWeekend/driverPanel/Reg2026Texts", "common/lib/classnames", "common/lib/preact", "common/util/CSSUtil", "project/data/GameTypes"], function (require, exports, DataStoreComponent, DS, Reg2026Texts_1, classnames_1, preact, CSSUtil_1, GameTypes_1) {
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
    //   Bandeau Reg2026Telemetry, au-dessus du nom du pilote, sur deux lignes : en haut la jauge OVERTAKE (crédit
    //   d'énergie Overtake Mode restant, 0,5 MJ au départ, lu dans Reg2026/state.json écrit par Reg2026Patch.dll
    //   toutes les 100 ms ; la voiture est retrouvée par sa position en course) ; en bas vitesse, batterie, état ERS
    //   (déploie / recharge / neutre) et énergie déployée dans le tour (ersDeploy, sur 4 MJ comme l'écran Stratégies ERS). Quand state.json est lu, la case
    //   OVERTAKE suit l'avantage au dépassement réel de la DLL (sur 2 km après chaque détection à moins d'1 s) au lieu de
    //   l'estimation par l'écart au passage de la ligne ; la barre de la jauge s'allume pendant le déploiement forcé (le crédit est gardé tant que la voiture devant
    //   n'est pas à moins de 0,6 s).
    Object.defineProperty(exports, "__esModule", { value: true });
    exports.DRSDisplay = void 0;
    (0, CSSUtil_1.loadCSS)('project/components/raceWeekend/DRSDisplay');
    (0, CSSUtil_1.loadCSS)('project/components/raceWeekend/Reg2026Modes');
    const EDRSState = GameTypes_1.EDRSState;
    const EERSState = GameTypes_1.EERSState;
    const STANDINGS = ['RaceSim', 'RaceStandings'];
    const OVERTAKE_GAP = 1.0;
    const CHECK_DELAY_MS = 1500;
    const MAX_DRIVER_ID = 64;
    const STATE_URL = 'Reg2026/state.json';
    const STATE_POLL_MS = 250;
    const STATE_STALE_MS = 2000;
    const OVERTAKE_CREDIT = 0.125;
    const BATTERY_MJ = 4.0;
    // un seul lecteur pour tous les bandeaux : dernier état lu et date de lecture
    const shared = { state: undefined, readAt: 0, timer: undefined, users: 0 };
    function pollState() {
        try {
            const xr = new XMLHttpRequest();
            xr.open('GET', STATE_URL, true);
            xr.onreadystatechange = () => {
                if (xr.readyState !== 4)
                    return;
                try {
                    const data = JSON.parse(xr.responseText);
                    if (data && data.cars) {
                        shared.state = data;
                        shared.readAt = Date.now();
                    }
                }
                catch (e) { }
            };
            xr.send();
        }
        catch (e) { }
    }
    function startPolling() {
        if (shared.users++ === 0)
            shared.timer = setInterval(pollState, STATE_POLL_MS);
    }
    function stopPolling() {
        if (--shared.users <= 0) {
            shared.users = 0;
            clearInterval(shared.timer);
            shared.timer = undefined;
        }
    }
    /// entrée de state.json pour cette voiture : par position en course (1 = en tête), sinon par index
    function carState(racePos, driverIndex) {
        const s = shared.state;
        if (!s || Date.now() - shared.readAt > STATE_STALE_MS || !s.rule)
            return undefined;
        return s.cars.find(c => c.p + 1 === racePos) || s.cars.find(c => c.i === driverIndex);
    }
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
    /// jauge OVERTAKE : crédit d'énergie restant (0,5 MJ au départ), allumée pendant le déploiement forcé
    function OvertakeGauge(props) {
        const car = props.car;
        const known = car !== undefined;
        const ratio = known ? Math.max(0, Math.min(1, car.c / OVERTAKE_CREDIT)) : 0;
        const active = known && car.b === 1;
        const mj = known ? (car.c * BATTERY_MJ).toFixed(2).replace('.', ',') + ' MJ' : '—';
        return preact.h("div", { className: (0, classnames_1.classNames)('Reg2026Overtake_row', { active, unknown: !known }) },
            preact.h("span", { className: (0, classnames_1.classNames)('Reg2026Telemetry_state ovt', { active }) }, 'OVERTAKE'),
            preact.h("div", { className: 'Reg2026Overtake_bar' },
                preact.h("div", { className: (0, classnames_1.classNames)('Reg2026Overtake_barFill', { active }), style: { width: (ratio * 100) + '%' } })),
            preact.h("span", { className: 'Reg2026Telemetry_value small' }, mj),
            preact.h("span", { className: 'Reg2026Telemetry_unit' }, '/ 0,50 MJ'));
    }
    /// bandeau au-dessus du nom du pilote : vitesse, batterie, jauge OVERTAKE, état ERS et énergie déployée dans le tour
    function Telemetry(props) {
        const battery = Math.max(0, Math.min(100, Math.round(props.battery || 0)));
        const ers = props.ersState == EERSState.Deploy ? 'deploy' : props.ersState == EERSState.Charge ? 'charge' : 'idle';
        const ersLabel = ers == 'deploy' ? 'DÉPLOIE' : ers == 'charge' ? 'RECHARGE' : 'NEUTRE';
        const deployed = (props.ersDeploy || 0).toFixed(1).replace('.', ',');
        return preact.h("div", { className: 'Reg2026Telemetry_root' },
            preact.h(OvertakeGauge, { car: props.car }),
            preact.h("div", { className: 'Reg2026Telemetry_row' },
            preact.h("div", { className: 'Reg2026Telemetry_cell speed' },
                preact.h("span", { className: 'Reg2026Telemetry_value' }, Math.round(props.speed || 0)),
                preact.h("span", { className: 'Reg2026Telemetry_unit' }, 'KM/H')),
            preact.h("div", { className: 'Reg2026Telemetry_cell battery' },
                preact.h("div", { className: 'Reg2026Telemetry_bar' },
                    preact.h("div", { className: (0, classnames_1.classNames)('Reg2026Telemetry_barFill', { low: battery < 25 }), style: { width: battery + '%' } })),
                preact.h("span", { className: 'Reg2026Telemetry_value' }, battery + ' %')),
            preact.h("div", { className: (0, classnames_1.classNames)('Reg2026Telemetry_cell ers', ers) },
                preact.h("span", { className: (0, classnames_1.classNames)('Reg2026Telemetry_state', ers) }, ersLabel),
                preact.h("span", { className: 'Reg2026Telemetry_unit' }, deployed + ' / 4,0 MJ'))));
    }
    class _DRSDisplay extends preact.Component {
        state = { straight: false, overtake: false, speed: 0, battery: 0, ersState: 0, ersDeploy: 0, racePos: 0, driverIndex: -1, car: undefined };
        _context = undefined;
        _lap = undefined;
        _timer = undefined;
        _stateTimer = undefined;
        onContextChanged(context, dataHelper) {
            this._context = context;
            this._lap = undefined;
            dataHelper.addPropertyListener(context, 'DRSState', this.onDRSStateChanged);
            dataHelper.addPropertyListener(context, 'lapCount', this.onLapChanged);
            dataHelper.addPropertyListener(context, 'speed', (v) => this.setState({ speed: Number(v) }));
            dataHelper.addPropertyListener(context, 'batteryPercentage', (v) => this.setState({ battery: Number(v) }));
            dataHelper.addPropertyListener(context, 'ersState', (v) => this.setState({ ersState: Number(v) }));
            dataHelper.addPropertyListener(context, 'ersDeploy', (v) => this.setState({ ersDeploy: Number(v) }));
            dataHelper.addPropertyListener(context, 'racePos', (v) => this.setState({ racePos: Number(v) }));
            dataHelper.addPropertyListener(context, 'driverIndex', (v) => this.setState({ driverIndex: Number(v) }));
            dataHelper.getAllPropertiesNow();
            if (this._stateTimer === undefined) {
                startPolling();
                this._stateTimer = setInterval(this.refreshCar, STATE_POLL_MS);
            }
        }
        componentWillUnmount() {
            clearTimeout(this._timer);
            if (this._stateTimer !== undefined) {
                clearInterval(this._stateTimer);
                this._stateTimer = undefined;
                stopPolling();
            }
        }
        /// recopie l'entrée de state.json de cette voiture ; la case OVERTAKE suit alors l'état réel de la DLL
        refreshCar = () => {
            const car = carState(this.state.racePos, this.state.driverIndex);
            const prev = this.state.car;
            const same = (car === undefined && prev === undefined) ||
                (car !== undefined && prev !== undefined && car.c === prev.c && car.b === prev.b && car.a === prev.a && car.i === prev.i);
            if (!same)
                this.setState({ car, overtake: car !== undefined ? car.a === 1 : this.state.overtake });
        };
        render(props, state) {
            return (!props.disabled &&
                preact.h("div", { className: 'Reg2026Modes_root' },
                    preact.h(Telemetry, { speed: state.speed, battery: state.battery, ersState: state.ersState, ersDeploy: state.ersDeploy, car: state.car }),
                    preact.h(ModeBox, { mode: 'straight', label: 'STRAIGHT', active: state.straight, focused: props.focused }),
                    preact.h(ModeBox, { mode: 'overtake', label: 'OVERTAKE', active: state.overtake, focused: props.focused })));
        }
        checkOvertake = () => {
            if (this.state.car !== undefined)
                return;  // état réel lu dans state.json
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
