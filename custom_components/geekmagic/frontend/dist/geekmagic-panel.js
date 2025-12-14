/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const L = globalThis, q = L.ShadowRoot && (L.ShadyCSS === void 0 || L.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, G = Symbol(), Z = /* @__PURE__ */ new WeakMap();
let ae = class {
  constructor(e, t, i) {
    if (this._$cssResult$ = !0, i !== G) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = e, this.t = t;
  }
  get styleSheet() {
    let e = this.o;
    const t = this.t;
    if (q && e === void 0) {
      const i = t !== void 0 && t.length === 1;
      i && (e = Z.get(t)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), i && Z.set(t, e));
    }
    return e;
  }
  toString() {
    return this.cssText;
  }
};
const pe = (s) => new ae(typeof s == "string" ? s : s + "", void 0, G), ue = (s, ...e) => {
  const t = s.length === 1 ? s[0] : e.reduce((i, r, o) => i + ((n) => {
    if (n._$cssResult$ === !0) return n.cssText;
    if (typeof n == "number") return n;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + n + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(r) + s[o + 1], s[0]);
  return new ae(t, s, G);
}, ge = (s, e) => {
  if (q) s.adoptedStyleSheets = e.map((t) => t instanceof CSSStyleSheet ? t : t.styleSheet);
  else for (const t of e) {
    const i = document.createElement("style"), r = L.litNonce;
    r !== void 0 && i.setAttribute("nonce", r), i.textContent = t.cssText, s.appendChild(i);
  }
}, Q = q ? (s) => s : (s) => s instanceof CSSStyleSheet ? ((e) => {
  let t = "";
  for (const i of e.cssRules) t += i.cssText;
  return pe(t);
})(s) : s;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: ve, defineProperty: _e, getOwnPropertyDescriptor: fe, getOwnPropertyNames: me, getOwnPropertySymbols: $e, getPrototypeOf: ye } = Object, y = globalThis, X = y.trustedTypes, we = X ? X.emptyScript : "", I = y.reactiveElementPolyfillSupport, C = (s, e) => s, D = { toAttribute(s, e) {
  switch (e) {
    case Boolean:
      s = s ? we : null;
      break;
    case Object:
    case Array:
      s = s == null ? s : JSON.stringify(s);
  }
  return s;
}, fromAttribute(s, e) {
  let t = s;
  switch (e) {
    case Boolean:
      t = s !== null;
      break;
    case Number:
      t = s === null ? null : Number(s);
      break;
    case Object:
    case Array:
      try {
        t = JSON.parse(s);
      } catch {
        t = null;
      }
  }
  return t;
} }, J = (s, e) => !ve(s, e), Y = { attribute: !0, type: String, converter: D, reflect: !1, useDefault: !1, hasChanged: J };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), y.litPropertyMetadata ?? (y.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let E = class extends HTMLElement {
  static addInitializer(e) {
    this._$Ei(), (this.l ?? (this.l = [])).push(e);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(e, t = Y) {
    if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
      const i = Symbol(), r = this.getPropertyDescriptor(e, i, t);
      r !== void 0 && _e(this.prototype, e, r);
    }
  }
  static getPropertyDescriptor(e, t, i) {
    const { get: r, set: o } = fe(this.prototype, e) ?? { get() {
      return this[t];
    }, set(n) {
      this[t] = n;
    } };
    return { get: r, set(n) {
      const l = r == null ? void 0 : r.call(this);
      o == null || o.call(this, n), this.requestUpdate(e, l, i);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(e) {
    return this.elementProperties.get(e) ?? Y;
  }
  static _$Ei() {
    if (this.hasOwnProperty(C("elementProperties"))) return;
    const e = ye(this);
    e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(C("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(C("properties"))) {
      const t = this.properties, i = [...me(t), ...$e(t)];
      for (const r of i) this.createProperty(r, t[r]);
    }
    const e = this[Symbol.metadata];
    if (e !== null) {
      const t = litPropertyMetadata.get(e);
      if (t !== void 0) for (const [i, r] of t) this.elementProperties.set(i, r);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t, i] of this.elementProperties) {
      const r = this._$Eu(t, i);
      r !== void 0 && this._$Eh.set(r, t);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(e) {
    const t = [];
    if (Array.isArray(e)) {
      const i = new Set(e.flat(1 / 0).reverse());
      for (const r of i) t.unshift(Q(r));
    } else e !== void 0 && t.push(Q(e));
    return t;
  }
  static _$Eu(e, t) {
    const i = t.attribute;
    return i === !1 ? void 0 : typeof i == "string" ? i : typeof e == "string" ? e.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    var e;
    this._$ES = new Promise((t) => this.enableUpdating = t), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), (e = this.constructor.l) == null || e.forEach((t) => t(this));
  }
  addController(e) {
    var t;
    (this._$EO ?? (this._$EO = /* @__PURE__ */ new Set())).add(e), this.renderRoot !== void 0 && this.isConnected && ((t = e.hostConnected) == null || t.call(e));
  }
  removeController(e) {
    var t;
    (t = this._$EO) == null || t.delete(e);
  }
  _$E_() {
    const e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
    for (const i of t.keys()) this.hasOwnProperty(i) && (e.set(i, this[i]), delete this[i]);
    e.size > 0 && (this._$Ep = e);
  }
  createRenderRoot() {
    const e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return ge(e, this.constructor.elementStyles), e;
  }
  connectedCallback() {
    var e;
    this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this.enableUpdating(!0), (e = this._$EO) == null || e.forEach((t) => {
      var i;
      return (i = t.hostConnected) == null ? void 0 : i.call(t);
    });
  }
  enableUpdating(e) {
  }
  disconnectedCallback() {
    var e;
    (e = this._$EO) == null || e.forEach((t) => {
      var i;
      return (i = t.hostDisconnected) == null ? void 0 : i.call(t);
    });
  }
  attributeChangedCallback(e, t, i) {
    this._$AK(e, i);
  }
  _$ET(e, t) {
    var o;
    const i = this.constructor.elementProperties.get(e), r = this.constructor._$Eu(e, i);
    if (r !== void 0 && i.reflect === !0) {
      const n = (((o = i.converter) == null ? void 0 : o.toAttribute) !== void 0 ? i.converter : D).toAttribute(t, i.type);
      this._$Em = e, n == null ? this.removeAttribute(r) : this.setAttribute(r, n), this._$Em = null;
    }
  }
  _$AK(e, t) {
    var o, n;
    const i = this.constructor, r = i._$Eh.get(e);
    if (r !== void 0 && this._$Em !== r) {
      const l = i.getPropertyOptions(r), a = typeof l.converter == "function" ? { fromAttribute: l.converter } : ((o = l.converter) == null ? void 0 : o.fromAttribute) !== void 0 ? l.converter : D;
      this._$Em = r;
      const h = a.fromAttribute(t, l.type);
      this[r] = h ?? ((n = this._$Ej) == null ? void 0 : n.get(r)) ?? h, this._$Em = null;
    }
  }
  requestUpdate(e, t, i) {
    var r;
    if (e !== void 0) {
      const o = this.constructor, n = this[e];
      if (i ?? (i = o.getPropertyOptions(e)), !((i.hasChanged ?? J)(n, t) || i.useDefault && i.reflect && n === ((r = this._$Ej) == null ? void 0 : r.get(e)) && !this.hasAttribute(o._$Eu(e, i)))) return;
      this.C(e, t, i);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(e, t, { useDefault: i, reflect: r, wrapped: o }, n) {
    i && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(e) && (this._$Ej.set(e, n ?? t ?? this[e]), o !== !0 || n !== void 0) || (this._$AL.has(e) || (this.hasUpdated || i || (t = void 0), this._$AL.set(e, t)), r === !0 && this._$Em !== e && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(e));
  }
  async _$EP() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (t) {
      Promise.reject(t);
    }
    const e = this.scheduleUpdate();
    return e != null && await e, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    var i;
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this._$Ep) {
        for (const [o, n] of this._$Ep) this[o] = n;
        this._$Ep = void 0;
      }
      const r = this.constructor.elementProperties;
      if (r.size > 0) for (const [o, n] of r) {
        const { wrapped: l } = n, a = this[o];
        l !== !0 || this._$AL.has(o) || a === void 0 || this.C(o, void 0, n, a);
      }
    }
    let e = !1;
    const t = this._$AL;
    try {
      e = this.shouldUpdate(t), e ? (this.willUpdate(t), (i = this._$EO) == null || i.forEach((r) => {
        var o;
        return (o = r.hostUpdate) == null ? void 0 : o.call(r);
      }), this.update(t)) : this._$EM();
    } catch (r) {
      throw e = !1, this._$EM(), r;
    }
    e && this._$AE(t);
  }
  willUpdate(e) {
  }
  _$AE(e) {
    var t;
    (t = this._$EO) == null || t.forEach((i) => {
      var r;
      return (r = i.hostUpdated) == null ? void 0 : r.call(i);
    }), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(e) {
    return !0;
  }
  update(e) {
    this._$Eq && (this._$Eq = this._$Eq.forEach((t) => this._$ET(t, this[t]))), this._$EM();
  }
  updated(e) {
  }
  firstUpdated(e) {
  }
};
E.elementStyles = [], E.shadowRootOptions = { mode: "open" }, E[C("elementProperties")] = /* @__PURE__ */ new Map(), E[C("finalized")] = /* @__PURE__ */ new Map(), I == null || I({ ReactiveElement: E }), (y.reactiveElementVersions ?? (y.reactiveElementVersions = [])).push("2.1.1");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const V = globalThis, j = V.trustedTypes, ee = j ? j.createPolicy("lit-html", { createHTML: (s) => s }) : void 0, le = "$lit$", $ = `lit$${Math.random().toFixed(9).slice(2)}$`, de = "?" + $, be = `<${de}>`, A = document, M = () => A.createComment(""), U = (s) => s === null || typeof s != "object" && typeof s != "function", K = Array.isArray, xe = (s) => K(s) || typeof (s == null ? void 0 : s[Symbol.iterator]) == "function", B = `[ 	
\f\r]`, k = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, te = /-->/g, ie = />/g, w = RegExp(`>|${B}(?:([^\\s"'>=/]+)(${B}*=${B}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), se = /'/g, re = /"/g, ce = /^(?:script|style|textarea|title)$/i, Ae = (s) => (e, ...t) => ({ _$litType$: s, strings: e, values: t }), p = Ae(1), S = Symbol.for("lit-noChange"), c = Symbol.for("lit-nothing"), oe = /* @__PURE__ */ new WeakMap(), b = A.createTreeWalker(A, 129);
function he(s, e) {
  if (!K(s) || !s.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return ee !== void 0 ? ee.createHTML(e) : e;
}
const Ee = (s, e) => {
  const t = s.length - 1, i = [];
  let r, o = e === 2 ? "<svg>" : e === 3 ? "<math>" : "", n = k;
  for (let l = 0; l < t; l++) {
    const a = s[l];
    let h, u, d = -1, _ = 0;
    for (; _ < a.length && (n.lastIndex = _, u = n.exec(a), u !== null); ) _ = n.lastIndex, n === k ? u[1] === "!--" ? n = te : u[1] !== void 0 ? n = ie : u[2] !== void 0 ? (ce.test(u[2]) && (r = RegExp("</" + u[2], "g")), n = w) : u[3] !== void 0 && (n = w) : n === w ? u[0] === ">" ? (n = r ?? k, d = -1) : u[1] === void 0 ? d = -2 : (d = n.lastIndex - u[2].length, h = u[1], n = u[3] === void 0 ? w : u[3] === '"' ? re : se) : n === re || n === se ? n = w : n === te || n === ie ? n = k : (n = w, r = void 0);
    const m = n === w && s[l + 1].startsWith("/>") ? " " : "";
    o += n === k ? a + be : d >= 0 ? (i.push(h), a.slice(0, d) + le + a.slice(d) + $ + m) : a + $ + (d === -2 ? l : m);
  }
  return [he(s, o + (s[t] || "<?>") + (e === 2 ? "</svg>" : e === 3 ? "</math>" : "")), i];
};
class T {
  constructor({ strings: e, _$litType$: t }, i) {
    let r;
    this.parts = [];
    let o = 0, n = 0;
    const l = e.length - 1, a = this.parts, [h, u] = Ee(e, t);
    if (this.el = T.createElement(h, i), b.currentNode = this.el.content, t === 2 || t === 3) {
      const d = this.el.content.firstChild;
      d.replaceWith(...d.childNodes);
    }
    for (; (r = b.nextNode()) !== null && a.length < l; ) {
      if (r.nodeType === 1) {
        if (r.hasAttributes()) for (const d of r.getAttributeNames()) if (d.endsWith(le)) {
          const _ = u[n++], m = r.getAttribute(d).split($), R = /([.?@])?(.*)/.exec(_);
          a.push({ type: 1, index: o, name: R[2], strings: m, ctor: R[1] === "." ? Pe : R[1] === "?" ? ke : R[1] === "@" ? Ce : z }), r.removeAttribute(d);
        } else d.startsWith($) && (a.push({ type: 6, index: o }), r.removeAttribute(d));
        if (ce.test(r.tagName)) {
          const d = r.textContent.split($), _ = d.length - 1;
          if (_ > 0) {
            r.textContent = j ? j.emptyScript : "";
            for (let m = 0; m < _; m++) r.append(d[m], M()), b.nextNode(), a.push({ type: 2, index: ++o });
            r.append(d[_], M());
          }
        }
      } else if (r.nodeType === 8) if (r.data === de) a.push({ type: 2, index: o });
      else {
        let d = -1;
        for (; (d = r.data.indexOf($, d + 1)) !== -1; ) a.push({ type: 7, index: o }), d += $.length - 1;
      }
      o++;
    }
  }
  static createElement(e, t) {
    const i = A.createElement("template");
    return i.innerHTML = e, i;
  }
}
function P(s, e, t = s, i) {
  var n, l;
  if (e === S) return e;
  let r = i !== void 0 ? (n = t._$Co) == null ? void 0 : n[i] : t._$Cl;
  const o = U(e) ? void 0 : e._$litDirective$;
  return (r == null ? void 0 : r.constructor) !== o && ((l = r == null ? void 0 : r._$AO) == null || l.call(r, !1), o === void 0 ? r = void 0 : (r = new o(s), r._$AT(s, t, i)), i !== void 0 ? (t._$Co ?? (t._$Co = []))[i] = r : t._$Cl = r), r !== void 0 && (e = P(s, r._$AS(s, e.values), r, i)), e;
}
class Se {
  constructor(e, t) {
    this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(e) {
    const { el: { content: t }, parts: i } = this._$AD, r = ((e == null ? void 0 : e.creationScope) ?? A).importNode(t, !0);
    b.currentNode = r;
    let o = b.nextNode(), n = 0, l = 0, a = i[0];
    for (; a !== void 0; ) {
      if (n === a.index) {
        let h;
        a.type === 2 ? h = new H(o, o.nextSibling, this, e) : a.type === 1 ? h = new a.ctor(o, a.name, a.strings, this, e) : a.type === 6 && (h = new Ve(o, this, e)), this._$AV.push(h), a = i[++l];
      }
      n !== (a == null ? void 0 : a.index) && (o = b.nextNode(), n++);
    }
    return b.currentNode = A, r;
  }
  p(e) {
    let t = 0;
    for (const i of this._$AV) i !== void 0 && (i.strings !== void 0 ? (i._$AI(e, i, t), t += i.strings.length - 2) : i._$AI(e[t])), t++;
  }
}
class H {
  get _$AU() {
    var e;
    return ((e = this._$AM) == null ? void 0 : e._$AU) ?? this._$Cv;
  }
  constructor(e, t, i, r) {
    this.type = 2, this._$AH = c, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = i, this.options = r, this._$Cv = (r == null ? void 0 : r.isConnected) ?? !0;
  }
  get parentNode() {
    let e = this._$AA.parentNode;
    const t = this._$AM;
    return t !== void 0 && (e == null ? void 0 : e.nodeType) === 11 && (e = t.parentNode), e;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(e, t = this) {
    e = P(this, e, t), U(e) ? e === c || e == null || e === "" ? (this._$AH !== c && this._$AR(), this._$AH = c) : e !== this._$AH && e !== S && this._(e) : e._$litType$ !== void 0 ? this.$(e) : e.nodeType !== void 0 ? this.T(e) : xe(e) ? this.k(e) : this._(e);
  }
  O(e) {
    return this._$AA.parentNode.insertBefore(e, this._$AB);
  }
  T(e) {
    this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
  }
  _(e) {
    this._$AH !== c && U(this._$AH) ? this._$AA.nextSibling.data = e : this.T(A.createTextNode(e)), this._$AH = e;
  }
  $(e) {
    var o;
    const { values: t, _$litType$: i } = e, r = typeof i == "number" ? this._$AC(e) : (i.el === void 0 && (i.el = T.createElement(he(i.h, i.h[0]), this.options)), i);
    if (((o = this._$AH) == null ? void 0 : o._$AD) === r) this._$AH.p(t);
    else {
      const n = new Se(r, this), l = n.u(this.options);
      n.p(t), this.T(l), this._$AH = n;
    }
  }
  _$AC(e) {
    let t = oe.get(e.strings);
    return t === void 0 && oe.set(e.strings, t = new T(e)), t;
  }
  k(e) {
    K(this._$AH) || (this._$AH = [], this._$AR());
    const t = this._$AH;
    let i, r = 0;
    for (const o of e) r === t.length ? t.push(i = new H(this.O(M()), this.O(M()), this, this.options)) : i = t[r], i._$AI(o), r++;
    r < t.length && (this._$AR(i && i._$AB.nextSibling, r), t.length = r);
  }
  _$AR(e = this._$AA.nextSibling, t) {
    var i;
    for ((i = this._$AP) == null ? void 0 : i.call(this, !1, !0, t); e !== this._$AB; ) {
      const r = e.nextSibling;
      e.remove(), e = r;
    }
  }
  setConnected(e) {
    var t;
    this._$AM === void 0 && (this._$Cv = e, (t = this._$AP) == null || t.call(this, e));
  }
}
class z {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(e, t, i, r, o) {
    this.type = 1, this._$AH = c, this._$AN = void 0, this.element = e, this.name = t, this._$AM = r, this.options = o, i.length > 2 || i[0] !== "" || i[1] !== "" ? (this._$AH = Array(i.length - 1).fill(new String()), this.strings = i) : this._$AH = c;
  }
  _$AI(e, t = this, i, r) {
    const o = this.strings;
    let n = !1;
    if (o === void 0) e = P(this, e, t, 0), n = !U(e) || e !== this._$AH && e !== S, n && (this._$AH = e);
    else {
      const l = e;
      let a, h;
      for (e = o[0], a = 0; a < o.length - 1; a++) h = P(this, l[i + a], t, a), h === S && (h = this._$AH[a]), n || (n = !U(h) || h !== this._$AH[a]), h === c ? e = c : e !== c && (e += (h ?? "") + o[a + 1]), this._$AH[a] = h;
    }
    n && !r && this.j(e);
  }
  j(e) {
    e === c ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
  }
}
class Pe extends z {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(e) {
    this.element[this.name] = e === c ? void 0 : e;
  }
}
class ke extends z {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(e) {
    this.element.toggleAttribute(this.name, !!e && e !== c);
  }
}
class Ce extends z {
  constructor(e, t, i, r, o) {
    super(e, t, i, r, o), this.type = 5;
  }
  _$AI(e, t = this) {
    if ((e = P(this, e, t, 0) ?? c) === S) return;
    const i = this._$AH, r = e === c && i !== c || e.capture !== i.capture || e.once !== i.once || e.passive !== i.passive, o = e !== c && (i === c || r);
    r && this.element.removeEventListener(this.name, this, i), o && this.element.addEventListener(this.name, this, e), this._$AH = e;
  }
  handleEvent(e) {
    var t;
    typeof this._$AH == "function" ? this._$AH.call(((t = this.options) == null ? void 0 : t.host) ?? this.element, e) : this._$AH.handleEvent(e);
  }
}
class Ve {
  constructor(e, t, i) {
    this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = i;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(e) {
    P(this, e);
  }
}
const W = V.litHtmlPolyfillSupport;
W == null || W(T, H), (V.litHtmlVersions ?? (V.litHtmlVersions = [])).push("3.3.1");
const Oe = (s, e, t) => {
  const i = (t == null ? void 0 : t.renderBefore) ?? e;
  let r = i._$litPart$;
  if (r === void 0) {
    const o = (t == null ? void 0 : t.renderBefore) ?? null;
    i._$litPart$ = r = new H(e.insertBefore(M(), o), o, void 0, t ?? {});
  }
  return r._$AI(s), r;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const x = globalThis;
class O extends E {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    var t;
    const e = super.createRenderRoot();
    return (t = this.renderOptions).renderBefore ?? (t.renderBefore = e.firstChild), e;
  }
  update(e) {
    const t = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Oe(t, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    var e;
    super.connectedCallback(), (e = this._$Do) == null || e.setConnected(!0);
  }
  disconnectedCallback() {
    var e;
    super.disconnectedCallback(), (e = this._$Do) == null || e.setConnected(!1);
  }
  render() {
    return S;
  }
}
var ne;
O._$litElement$ = !0, O.finalized = !0, (ne = x.litElementHydrateSupport) == null || ne.call(x, { LitElement: O });
const F = x.litElementPolyfillSupport;
F == null || F({ LitElement: O });
(x.litElementVersions ?? (x.litElementVersions = [])).push("4.2.1");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Me = (s) => (e, t) => {
  t !== void 0 ? t.addInitializer(() => {
    customElements.define(s, e);
  }) : customElements.define(s, e);
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Ue = { attribute: !0, type: String, converter: D, reflect: !1, hasChanged: J }, Te = (s = Ue, e, t) => {
  const { kind: i, metadata: r } = t;
  let o = globalThis.litPropertyMetadata.get(r);
  if (o === void 0 && globalThis.litPropertyMetadata.set(r, o = /* @__PURE__ */ new Map()), i === "setter" && ((s = Object.create(s)).wrapped = !0), o.set(t.name, s), i === "accessor") {
    const { name: n } = t;
    return { set(l) {
      const a = e.get.call(this);
      e.set.call(this, l), this.requestUpdate(n, a, s);
    }, init(l) {
      return l !== void 0 && this.C(n, void 0, s, l), l;
    } };
  }
  if (i === "setter") {
    const { name: n } = t;
    return function(l) {
      const a = this[n];
      e.call(this, l), this.requestUpdate(n, a, s);
    };
  }
  throw Error("Unsupported decorator location: " + i);
};
function N(s) {
  return (e, t) => typeof t == "object" ? Te(s, e, t) : ((i, r, o) => {
    const n = r.hasOwnProperty(o);
    return r.constructor.createProperty(o, i), n ? Object.getOwnPropertyDescriptor(r, o) : void 0;
  })(s, e, t);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function f(s) {
  return N({ ...s, state: !0, attribute: !1 });
}
var He = Object.defineProperty, Ne = Object.getOwnPropertyDescriptor, v = (s, e, t, i) => {
  for (var r = i > 1 ? void 0 : i ? Ne(e, t) : e, o = s.length - 1, n; o >= 0; o--)
    (n = s[o]) && (r = (i ? n(e, t, r) : n(r)) || r);
  return i && r && He(e, t, r), r;
};
function Re(s, e) {
  let t;
  return (...i) => {
    clearTimeout(t), t = setTimeout(() => s(...i), e);
  };
}
let g = class extends O {
  constructor() {
    super(...arguments), this.narrow = !1, this._page = "views", this._config = null, this._views = [], this._devices = [], this._editingView = null, this._previewImage = null, this._previewLoading = !1, this._loading = !0, this._saving = !1, this._refreshPreview = Re(async () => {
      if (this._editingView) {
        this._previewLoading = !0;
        try {
          const s = await this.hass.connection.sendMessagePromise({
            type: "geekmagic/preview/render",
            view_config: {
              layout: this._editingView.layout,
              theme: this._editingView.theme,
              widgets: this._editingView.widgets
            }
          });
          this._previewImage = s.image;
        } catch (s) {
          console.error("Failed to render preview:", s);
        } finally {
          this._previewLoading = !1;
        }
      }
    }, 500);
  }
  firstUpdated() {
    this._loadData();
  }
  async _loadData() {
    this._loading = !0;
    try {
      const [s, e, t] = await Promise.all([
        this.hass.connection.sendMessagePromise({
          type: "geekmagic/config"
        }),
        this.hass.connection.sendMessagePromise({
          type: "geekmagic/views/list"
        }),
        this.hass.connection.sendMessagePromise({
          type: "geekmagic/devices/list"
        })
      ]);
      this._config = s, this._views = e.views, this._devices = t.devices;
    } catch (s) {
      console.error("Failed to load GeekMagic config:", s);
    } finally {
      this._loading = !1;
    }
  }
  async _createView() {
    const s = prompt("Enter view name:", "New View");
    if (s)
      try {
        const e = await this.hass.connection.sendMessagePromise({
          type: "geekmagic/views/create",
          name: s,
          layout: "grid_2x2",
          theme: "classic",
          widgets: []
        });
        this._views = [...this._views, e.view], this._editView(e.view);
      } catch (e) {
        console.error("Failed to create view:", e), alert("Failed to create view");
      }
  }
  _editView(s) {
    this._editingView = { ...s, widgets: [...s.widgets] }, this._page = "editor", this._refreshPreview();
  }
  async _saveView() {
    if (this._editingView) {
      this._saving = !0;
      try {
        await this.hass.connection.sendMessagePromise({
          type: "geekmagic/views/update",
          view_id: this._editingView.id,
          name: this._editingView.name,
          layout: this._editingView.layout,
          theme: this._editingView.theme,
          widgets: this._editingView.widgets
        }), this._views = this._views.map(
          (s) => s.id === this._editingView.id ? this._editingView : s
        ), this._page = "views", this._editingView = null;
      } catch (s) {
        console.error("Failed to save view:", s), alert("Failed to save view");
      } finally {
        this._saving = !1;
      }
    }
  }
  async _deleteView(s) {
    if (confirm(`Delete view "${s.name}"?`))
      try {
        await this.hass.connection.sendMessagePromise({
          type: "geekmagic/views/delete",
          view_id: s.id
        }), this._views = this._views.filter((e) => e.id !== s.id);
      } catch (e) {
        console.error("Failed to delete view:", e), alert("Failed to delete view");
      }
  }
  _updateEditingView(s) {
    this._editingView && (this._editingView = { ...this._editingView, ...s }, this._refreshPreview());
  }
  _updateWidget(s, e) {
    if (!this._editingView) return;
    const t = [...this._editingView.widgets], i = t.findIndex((r) => r.slot === s);
    i >= 0 ? t[i] = { ...t[i], ...e } : t.push({ slot: s, type: "clock", ...e }), this._editingView = { ...this._editingView, widgets: t }, this._refreshPreview();
  }
  async _toggleDeviceView(s, e, t) {
    let i;
    t ? i = [...s.assigned_views, e] : i = s.assigned_views.filter((r) => r !== e);
    try {
      await this.hass.connection.sendMessagePromise({
        type: "geekmagic/devices/assign_views",
        entry_id: s.entry_id,
        view_ids: i
      }), this._devices = this._devices.map(
        (r) => r.entry_id === s.entry_id ? { ...r, assigned_views: i } : r
      );
    } catch (r) {
      console.error("Failed to update device views:", r);
    }
  }
  render() {
    return this._loading ? p`
        <div class="loading">
          <span>Loading...</span>
        </div>
      ` : p`
      <div class="header">
        <span class="header-title">GeekMagic</span>
        ${this._page !== "editor" ? p`
              <div class="tabs">
                <button
                  class="tab ${this._page === "views" ? "active" : ""}"
                  @click=${() => this._page = "views"}
                >
                  Views
                </button>
                <button
                  class="tab ${this._page === "devices" ? "active" : ""}"
                  @click=${() => this._page = "devices"}
                >
                  Devices
                </button>
              </div>
            ` : c}
      </div>
      <div class="content">${this._renderPage()}</div>
    `;
  }
  _renderPage() {
    switch (this._page) {
      case "views":
        return this._renderViewsList();
      case "devices":
        return this._renderDevicesList();
      case "editor":
        return this._renderEditor();
    }
  }
  _renderViewsList() {
    return p`
      <div class="views-grid">
        ${this._views.map(
      (s) => p`
            <div class="view-card" @click=${() => this._editView(s)}>
              <div class="view-card-header">
                <span class="view-card-title">${s.name}</span>
                <button
                  class="btn btn-danger"
                  @click=${(e) => {
        e.stopPropagation(), this._deleteView(s);
      }}
                >
                  Delete
                </button>
              </div>
              <div class="view-card-meta">
                Layout: ${s.layout} | Theme: ${s.theme} | Widgets:
                ${s.widgets.length}
              </div>
            </div>
          `
    )}
        <div class="add-card" @click=${this._createView}>
          <span>+ Add View</span>
        </div>
      </div>
    `;
  }
  _renderDevicesList() {
    return this._devices.length === 0 ? p`<p>No GeekMagic devices configured.</p>` : p`
      <div class="devices-list">
        ${this._devices.map(
      (s) => p`
            <div class="device-card">
              <div class="device-header">
                <span class="device-name">${s.name}</span>
                <span
                  class="device-status ${s.online ? "online" : "offline"}"
                >
                  ${s.online ? "Online" : "Offline"}
                </span>
              </div>
              <div class="form-section-title">Assigned Views</div>
              ${this._views.map(
        (e) => p`
                  <label class="view-checkbox">
                    <input
                      type="checkbox"
                      ?checked=${s.assigned_views.includes(e.id)}
                      @change=${(t) => this._toggleDeviceView(
          s,
          e.id,
          t.target.checked
        )}
                    />
                    ${e.name}
                  </label>
                `
      )}
              ${this._views.length === 0 ? p`<p>No views available. Create a view first.</p>` : c}
            </div>
          `
    )}
      </div>
    `;
  }
  _renderEditor() {
    var e;
    if (!this._editingView || !this._config) return c;
    const s = ((e = this._config.layout_types[this._editingView.layout]) == null ? void 0 : e.slots) || 4;
    return p`
      <div class="editor-header">
        <button class="back-btn" @click=${() => this._page = "views"}>
          ← Back
        </button>
        <div class="form-field" style="flex: 1;">
          <input
            type="text"
            .value=${this._editingView.name}
            @input=${(t) => this._updateEditingView({
      name: t.target.value
    })}
            placeholder="View name"
          />
        </div>
        <button
          class="btn btn-primary"
          ?disabled=${this._saving}
          @click=${this._saveView}
        >
          ${this._saving ? "Saving..." : "Save"}
        </button>
      </div>

      <div class="editor-container">
        <div class="editor-form">
          <div class="form-section">
            <div class="form-row">
              <div class="form-field">
                <label>Layout</label>
                <select
                  .value=${this._editingView.layout}
                  @change=${(t) => this._updateEditingView({
      layout: t.target.value
    })}
                >
                  ${Object.entries(this._config.layout_types).map(
      ([t, i]) => p`<option value=${t}>
                        ${i.name} (${i.slots} slots)
                      </option>`
    )}
                </select>
              </div>
              <div class="form-field">
                <label>Theme</label>
                <select
                  .value=${this._editingView.theme}
                  @change=${(t) => this._updateEditingView({
      theme: t.target.value
    })}
                >
                  ${Object.entries(this._config.themes).map(
      ([t, i]) => p`<option value=${t}>${i}</option>`
    )}
                </select>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="form-section-title">Widgets</div>
            <div class="slots-grid">
              ${Array.from(
      { length: s },
      (t, i) => this._renderSlotEditor(i)
    )}
            </div>
          </div>
        </div>

        <div class="editor-preview">
          <h3>Preview</h3>
          ${this._previewLoading ? p`<div class="preview-placeholder">Loading...</div>` : this._previewImage ? p`<img
                  class="preview-image"
                  src="data:image/png;base64,${this._previewImage}"
                  alt="Preview"
                />` : p`<div class="preview-placeholder">No preview</div>`}
          <button
            class="btn btn-secondary"
            style="margin-top: 16px;"
            @click=${() => this._refreshPreview()}
          >
            Refresh
          </button>
        </div>
      </div>
    `;
  }
  _renderSlotEditor(s) {
    var r;
    if (!this._config) return c;
    const e = (r = this._editingView) == null ? void 0 : r.widgets.find((o) => o.slot === s), t = (e == null ? void 0 : e.type) || "", i = this._config.widget_types[t];
    return p`
      <div class="slot-card">
        <div class="slot-header">Slot ${s + 1}</div>
        <div class="form-field">
          <label>Widget Type</label>
          <select
            .value=${t}
            @change=${(o) => this._updateWidget(s, {
      type: o.target.value
    })}
          >
            <option value="">-- Empty --</option>
            ${Object.entries(this._config.widget_types).map(
      ([o, n]) => p`<option value=${o}>${n.name}</option>`
    )}
          </select>
        </div>

        ${i != null && i.needs_entity ? p`
              <div class="form-field">
                <label>Entity</label>
                <input
                  type="text"
                  .value=${(e == null ? void 0 : e.entity_id) || ""}
                  @input=${(o) => this._updateWidget(s, {
      entity_id: o.target.value
    })}
                  placeholder="sensor.example"
                />
              </div>
            ` : c}

        <div class="form-field">
          <label>Label (optional)</label>
          <input
            type="text"
            .value=${(e == null ? void 0 : e.label) || ""}
            @input=${(o) => this._updateWidget(s, {
      label: o.target.value
    })}
            placeholder="Custom label"
          />
        </div>
      </div>
    `;
  }
};
g.styles = ue`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      --mdc-theme-primary: var(--primary-color);
    }

    .header {
      display: flex;
      align-items: center;
      padding: 8px 16px;
      border-bottom: 1px solid var(--divider-color);
      background: var(--app-header-background-color);
    }

    .header-title {
      flex: 1;
      font-size: 20px;
      font-weight: 500;
      margin-left: 16px;
    }

    .tabs {
      display: flex;
      gap: 8px;
      margin-left: auto;
    }

    .tab {
      padding: 8px 16px;
      border: none;
      background: none;
      cursor: pointer;
      border-radius: 4px;
      font-size: 14px;
      color: var(--primary-text-color);
    }

    .tab:hover {
      background: var(--secondary-background-color);
    }

    .tab.active {
      background: var(--primary-color);
      color: var(--text-primary-color);
    }

    .content {
      flex: 1;
      overflow: auto;
      padding: 16px;
    }

    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
    }

    /* Views List */
    .views-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
    }

    .view-card {
      background: var(--card-background-color);
      border-radius: 8px;
      padding: 16px;
      cursor: pointer;
      border: 1px solid var(--divider-color);
      transition: box-shadow 0.2s;
    }

    .view-card:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }

    .view-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }

    .view-card-title {
      font-size: 16px;
      font-weight: 500;
    }

    .view-card-meta {
      font-size: 12px;
      color: var(--secondary-text-color);
    }

    .add-card {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100px;
      border: 2px dashed var(--divider-color);
      border-radius: 8px;
      cursor: pointer;
      color: var(--secondary-text-color);
    }

    .add-card:hover {
      border-color: var(--primary-color);
      color: var(--primary-color);
    }

    /* Editor Layout */
    .editor-container {
      display: flex;
      gap: 24px;
      height: 100%;
    }

    .editor-form {
      flex: 7;
      overflow-y: auto;
    }

    .editor-preview {
      flex: 3;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
      background: var(--secondary-background-color);
      border-radius: 8px;
    }

    .preview-image {
      width: 240px;
      height: 240px;
      border-radius: 8px;
      background: #000;
      object-fit: contain;
    }

    .preview-placeholder {
      width: 240px;
      height: 240px;
      border-radius: 8px;
      background: #1a1a1a;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #666;
    }

    /* Form Elements */
    .form-section {
      margin-bottom: 24px;
    }

    .form-section-title {
      font-size: 14px;
      font-weight: 500;
      margin-bottom: 8px;
      color: var(--secondary-text-color);
    }

    .form-row {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;
    }

    .form-field {
      flex: 1;
    }

    .form-field label {
      display: block;
      font-size: 12px;
      margin-bottom: 4px;
      color: var(--secondary-text-color);
    }

    .form-field input,
    .form-field select {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid var(--divider-color);
      border-radius: 4px;
      background: var(--card-background-color);
      color: var(--primary-text-color);
      font-size: 14px;
    }

    .form-field input:focus,
    .form-field select:focus {
      outline: none;
      border-color: var(--primary-color);
    }

    /* Slots Grid */
    .slots-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 16px;
    }

    .slot-card {
      background: var(--card-background-color);
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      padding: 16px;
    }

    .slot-header {
      font-size: 14px;
      font-weight: 500;
      margin-bottom: 12px;
      color: var(--primary-text-color);
    }

    /* Buttons */
    .btn {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      transition: background 0.2s;
    }

    .btn-primary {
      background: var(--primary-color);
      color: var(--text-primary-color);
    }

    .btn-primary:hover {
      opacity: 0.9;
    }

    .btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .btn-secondary {
      background: var(--secondary-background-color);
      color: var(--primary-text-color);
    }

    .btn-secondary:hover {
      background: var(--divider-color);
    }

    .btn-danger {
      background: var(--error-color, #db4437);
      color: white;
    }

    .editor-header {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 24px;
    }

    .back-btn {
      background: none;
      border: none;
      cursor: pointer;
      padding: 8px;
      color: var(--primary-text-color);
    }

    /* Devices List */
    .devices-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .device-card {
      background: var(--card-background-color);
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      padding: 16px;
    }

    .device-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }

    .device-name {
      font-size: 16px;
      font-weight: 500;
    }

    .device-status {
      font-size: 12px;
      padding: 4px 8px;
      border-radius: 4px;
    }

    .device-status.online {
      background: #4caf50;
      color: white;
    }

    .device-status.offline {
      background: #f44336;
      color: white;
    }

    .view-checkbox {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 0;
    }

    .view-checkbox input {
      width: 18px;
      height: 18px;
    }
  `;
v([
  N({ attribute: !1 })
], g.prototype, "hass", 2);
v([
  N({ type: Boolean })
], g.prototype, "narrow", 2);
v([
  N({ attribute: !1 })
], g.prototype, "route", 2);
v([
  N({ attribute: !1 })
], g.prototype, "panel", 2);
v([
  f()
], g.prototype, "_page", 2);
v([
  f()
], g.prototype, "_config", 2);
v([
  f()
], g.prototype, "_views", 2);
v([
  f()
], g.prototype, "_devices", 2);
v([
  f()
], g.prototype, "_editingView", 2);
v([
  f()
], g.prototype, "_previewImage", 2);
v([
  f()
], g.prototype, "_previewLoading", 2);
v([
  f()
], g.prototype, "_loading", 2);
v([
  f()
], g.prototype, "_saving", 2);
g = v([
  Me("geekmagic-panel")
], g);
export {
  g as GeekMagicPanel
};
