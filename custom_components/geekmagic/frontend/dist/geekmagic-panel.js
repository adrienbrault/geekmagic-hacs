/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const U = globalThis, K = U.ShadowRoot && (U.ShadyCSS === void 0 || U.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, J = Symbol(), Q = /* @__PURE__ */ new WeakMap();
let pe = class {
  constructor(e, t, s) {
    if (this._$cssResult$ = !0, s !== J) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = e, this.t = t;
  }
  get styleSheet() {
    let e = this.o;
    const t = this.t;
    if (K && e === void 0) {
      const s = t !== void 0 && t.length === 1;
      s && (e = Q.get(t)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), s && Q.set(t, e));
    }
    return e;
  }
  toString() {
    return this.cssText;
  }
};
const _e = (i) => new pe(typeof i == "string" ? i : i + "", void 0, J), $e = (i, ...e) => {
  const t = i.length === 1 ? i[0] : e.reduce((s, r, a) => s + ((o) => {
    if (o._$cssResult$ === !0) return o.cssText;
    if (typeof o == "number") return o;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + o + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(r) + i[a + 1], i[0]);
  return new pe(t, i, J);
}, we = (i, e) => {
  if (K) i.adoptedStyleSheets = e.map((t) => t instanceof CSSStyleSheet ? t : t.styleSheet);
  else for (const t of e) {
    const s = document.createElement("style"), r = U.litNonce;
    r !== void 0 && s.setAttribute("nonce", r), s.textContent = t.cssText, i.appendChild(s);
  }
}, ee = K ? (i) => i : (i) => i instanceof CSSStyleSheet ? ((e) => {
  let t = "";
  for (const s of e.cssRules) t += s.cssText;
  return _e(t);
})(i) : i;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: ye, defineProperty: be, getOwnPropertyDescriptor: xe, getOwnPropertyNames: Ae, getOwnPropertySymbols: Ee, getPrototypeOf: Ve } = Object, w = globalThis, te = w.trustedTypes, ke = te ? te.emptyScript : "", R = w.reactiveElementPolyfillSupport, C = (i, e) => i, z = { toAttribute(i, e) {
  switch (e) {
    case Boolean:
      i = i ? ke : null;
      break;
    case Object:
    case Array:
      i = i == null ? i : JSON.stringify(i);
  }
  return i;
}, fromAttribute(i, e) {
  let t = i;
  switch (e) {
    case Boolean:
      t = i !== null;
      break;
    case Number:
      t = i === null ? null : Number(i);
      break;
    case Object:
    case Array:
      try {
        t = JSON.parse(i);
      } catch {
        t = null;
      }
  }
  return t;
} }, X = (i, e) => !ye(i, e), ie = { attribute: !0, type: String, converter: z, reflect: !1, useDefault: !1, hasChanged: X };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), w.litPropertyMetadata ?? (w.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let V = class extends HTMLElement {
  static addInitializer(e) {
    this._$Ei(), (this.l ?? (this.l = [])).push(e);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(e, t = ie) {
    if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
      const s = Symbol(), r = this.getPropertyDescriptor(e, s, t);
      r !== void 0 && be(this.prototype, e, r);
    }
  }
  static getPropertyDescriptor(e, t, s) {
    const { get: r, set: a } = xe(this.prototype, e) ?? { get() {
      return this[t];
    }, set(o) {
      this[t] = o;
    } };
    return { get: r, set(o) {
      const n = r == null ? void 0 : r.call(this);
      a == null || a.call(this, o), this.requestUpdate(e, n, s);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(e) {
    return this.elementProperties.get(e) ?? ie;
  }
  static _$Ei() {
    if (this.hasOwnProperty(C("elementProperties"))) return;
    const e = Ve(this);
    e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(C("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(C("properties"))) {
      const t = this.properties, s = [...Ae(t), ...Ee(t)];
      for (const r of s) this.createProperty(r, t[r]);
    }
    const e = this[Symbol.metadata];
    if (e !== null) {
      const t = litPropertyMetadata.get(e);
      if (t !== void 0) for (const [s, r] of t) this.elementProperties.set(s, r);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t, s] of this.elementProperties) {
      const r = this._$Eu(t, s);
      r !== void 0 && this._$Eh.set(r, t);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(e) {
    const t = [];
    if (Array.isArray(e)) {
      const s = new Set(e.flat(1 / 0).reverse());
      for (const r of s) t.unshift(ee(r));
    } else e !== void 0 && t.push(ee(e));
    return t;
  }
  static _$Eu(e, t) {
    const s = t.attribute;
    return s === !1 ? void 0 : typeof s == "string" ? s : typeof e == "string" ? e.toLowerCase() : void 0;
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
    for (const s of t.keys()) this.hasOwnProperty(s) && (e.set(s, this[s]), delete this[s]);
    e.size > 0 && (this._$Ep = e);
  }
  createRenderRoot() {
    const e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return we(e, this.constructor.elementStyles), e;
  }
  connectedCallback() {
    var e;
    this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this.enableUpdating(!0), (e = this._$EO) == null || e.forEach((t) => {
      var s;
      return (s = t.hostConnected) == null ? void 0 : s.call(t);
    });
  }
  enableUpdating(e) {
  }
  disconnectedCallback() {
    var e;
    (e = this._$EO) == null || e.forEach((t) => {
      var s;
      return (s = t.hostDisconnected) == null ? void 0 : s.call(t);
    });
  }
  attributeChangedCallback(e, t, s) {
    this._$AK(e, s);
  }
  _$ET(e, t) {
    var a;
    const s = this.constructor.elementProperties.get(e), r = this.constructor._$Eu(e, s);
    if (r !== void 0 && s.reflect === !0) {
      const o = (((a = s.converter) == null ? void 0 : a.toAttribute) !== void 0 ? s.converter : z).toAttribute(t, s.type);
      this._$Em = e, o == null ? this.removeAttribute(r) : this.setAttribute(r, o), this._$Em = null;
    }
  }
  _$AK(e, t) {
    var a, o;
    const s = this.constructor, r = s._$Eh.get(e);
    if (r !== void 0 && this._$Em !== r) {
      const n = s.getPropertyOptions(r), l = typeof n.converter == "function" ? { fromAttribute: n.converter } : ((a = n.converter) == null ? void 0 : a.fromAttribute) !== void 0 ? n.converter : z;
      this._$Em = r;
      const h = l.fromAttribute(t, n.type);
      this[r] = h ?? ((o = this._$Ej) == null ? void 0 : o.get(r)) ?? h, this._$Em = null;
    }
  }
  requestUpdate(e, t, s) {
    var r;
    if (e !== void 0) {
      const a = this.constructor, o = this[e];
      if (s ?? (s = a.getPropertyOptions(e)), !((s.hasChanged ?? X)(o, t) || s.useDefault && s.reflect && o === ((r = this._$Ej) == null ? void 0 : r.get(e)) && !this.hasAttribute(a._$Eu(e, s)))) return;
      this.C(e, t, s);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(e, t, { useDefault: s, reflect: r, wrapped: a }, o) {
    s && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(e) && (this._$Ej.set(e, o ?? t ?? this[e]), a !== !0 || o !== void 0) || (this._$AL.has(e) || (this.hasUpdated || s || (t = void 0), this._$AL.set(e, t)), r === !0 && this._$Em !== e && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(e));
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
    var s;
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this._$Ep) {
        for (const [a, o] of this._$Ep) this[a] = o;
        this._$Ep = void 0;
      }
      const r = this.constructor.elementProperties;
      if (r.size > 0) for (const [a, o] of r) {
        const { wrapped: n } = o, l = this[a];
        n !== !0 || this._$AL.has(a) || l === void 0 || this.C(a, void 0, o, l);
      }
    }
    let e = !1;
    const t = this._$AL;
    try {
      e = this.shouldUpdate(t), e ? (this.willUpdate(t), (s = this._$EO) == null || s.forEach((r) => {
        var a;
        return (a = r.hostUpdate) == null ? void 0 : a.call(r);
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
    (t = this._$EO) == null || t.forEach((s) => {
      var r;
      return (r = s.hostUpdated) == null ? void 0 : r.call(s);
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
V.elementStyles = [], V.shadowRootOptions = { mode: "open" }, V[C("elementProperties")] = /* @__PURE__ */ new Map(), V[C("finalized")] = /* @__PURE__ */ new Map(), R == null || R({ ReactiveElement: V }), (w.reactiveElementVersions ?? (w.reactiveElementVersions = [])).push("2.1.1");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const O = globalThis, j = O.trustedTypes, se = j ? j.createPolicy("lit-html", { createHTML: (i) => i }) : void 0, ue = "$lit$", $ = `lit$${Math.random().toFixed(9).slice(2)}$`, ge = "?" + $, Pe = `<${ge}>`, E = document, I = () => E.createComment(""), H = (i) => i === null || typeof i != "object" && typeof i != "function", Y = Array.isArray, Se = (i) => Y(i) || typeof (i == null ? void 0 : i[Symbol.iterator]) == "function", F = `[ 	
\f\r]`, S = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, re = /-->/g, ae = />/g, y = RegExp(`>|${F}(?:([^\\s"'>=/]+)(${F}*=${F}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), oe = /'/g, ne = /"/g, ve = /^(?:script|style|textarea|title)$/i, Ce = (i) => (e, ...t) => ({ _$litType$: i, strings: e, values: t }), c = Ce(1), k = Symbol.for("lit-noChange"), p = Symbol.for("lit-nothing"), le = /* @__PURE__ */ new WeakMap(), x = E.createTreeWalker(E, 129);
function me(i, e) {
  if (!Y(i) || !i.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return se !== void 0 ? se.createHTML(e) : e;
}
const Oe = (i, e) => {
  const t = i.length - 1, s = [];
  let r, a = e === 2 ? "<svg>" : e === 3 ? "<math>" : "", o = S;
  for (let n = 0; n < t; n++) {
    const l = i[n];
    let h, v, d = -1, f = 0;
    for (; f < l.length && (o.lastIndex = f, v = o.exec(l), v !== null); ) f = o.lastIndex, o === S ? v[1] === "!--" ? o = re : v[1] !== void 0 ? o = ae : v[2] !== void 0 ? (ve.test(v[2]) && (r = RegExp("</" + v[2], "g")), o = y) : v[3] !== void 0 && (o = y) : o === y ? v[0] === ">" ? (o = r ?? S, d = -1) : v[1] === void 0 ? d = -2 : (d = o.lastIndex - v[2].length, h = v[1], o = v[3] === void 0 ? y : v[3] === '"' ? ne : oe) : o === ne || o === oe ? o = y : o === re || o === ae ? o = S : (o = y, r = void 0);
    const _ = o === y && i[n + 1].startsWith("/>") ? " " : "";
    a += o === S ? l + Pe : d >= 0 ? (s.push(h), l.slice(0, d) + ue + l.slice(d) + $ + _) : l + $ + (d === -2 ? n : _);
  }
  return [me(i, a + (i[t] || "<?>") + (e === 2 ? "</svg>" : e === 3 ? "</math>" : "")), s];
};
class L {
  constructor({ strings: e, _$litType$: t }, s) {
    let r;
    this.parts = [];
    let a = 0, o = 0;
    const n = e.length - 1, l = this.parts, [h, v] = Oe(e, t);
    if (this.el = L.createElement(h, s), x.currentNode = this.el.content, t === 2 || t === 3) {
      const d = this.el.content.firstChild;
      d.replaceWith(...d.childNodes);
    }
    for (; (r = x.nextNode()) !== null && l.length < n; ) {
      if (r.nodeType === 1) {
        if (r.hasAttributes()) for (const d of r.getAttributeNames()) if (d.endsWith(ue)) {
          const f = v[o++], _ = r.getAttribute(d).split($), N = /([.?@])?(.*)/.exec(f);
          l.push({ type: 1, index: a, name: N[2], strings: _, ctor: N[1] === "." ? Ie : N[1] === "?" ? He : N[1] === "@" ? Le : W }), r.removeAttribute(d);
        } else d.startsWith($) && (l.push({ type: 6, index: a }), r.removeAttribute(d));
        if (ve.test(r.tagName)) {
          const d = r.textContent.split($), f = d.length - 1;
          if (f > 0) {
            r.textContent = j ? j.emptyScript : "";
            for (let _ = 0; _ < f; _++) r.append(d[_], I()), x.nextNode(), l.push({ type: 2, index: ++a });
            r.append(d[f], I());
          }
        }
      } else if (r.nodeType === 8) if (r.data === ge) l.push({ type: 2, index: a });
      else {
        let d = -1;
        for (; (d = r.data.indexOf($, d + 1)) !== -1; ) l.push({ type: 7, index: a }), d += $.length - 1;
      }
      a++;
    }
  }
  static createElement(e, t) {
    const s = E.createElement("template");
    return s.innerHTML = e, s;
  }
}
function P(i, e, t = i, s) {
  var o, n;
  if (e === k) return e;
  let r = s !== void 0 ? (o = t._$Co) == null ? void 0 : o[s] : t._$Cl;
  const a = H(e) ? void 0 : e._$litDirective$;
  return (r == null ? void 0 : r.constructor) !== a && ((n = r == null ? void 0 : r._$AO) == null || n.call(r, !1), a === void 0 ? r = void 0 : (r = new a(i), r._$AT(i, t, s)), s !== void 0 ? (t._$Co ?? (t._$Co = []))[s] = r : t._$Cl = r), r !== void 0 && (e = P(i, r._$AS(i, e.values), r, s)), e;
}
class Me {
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
    const { el: { content: t }, parts: s } = this._$AD, r = ((e == null ? void 0 : e.creationScope) ?? E).importNode(t, !0);
    x.currentNode = r;
    let a = x.nextNode(), o = 0, n = 0, l = s[0];
    for (; l !== void 0; ) {
      if (o === l.index) {
        let h;
        l.type === 2 ? h = new T(a, a.nextSibling, this, e) : l.type === 1 ? h = new l.ctor(a, l.name, l.strings, this, e) : l.type === 6 && (h = new Te(a, this, e)), this._$AV.push(h), l = s[++n];
      }
      o !== (l == null ? void 0 : l.index) && (a = x.nextNode(), o++);
    }
    return x.currentNode = E, r;
  }
  p(e) {
    let t = 0;
    for (const s of this._$AV) s !== void 0 && (s.strings !== void 0 ? (s._$AI(e, s, t), t += s.strings.length - 2) : s._$AI(e[t])), t++;
  }
}
class T {
  get _$AU() {
    var e;
    return ((e = this._$AM) == null ? void 0 : e._$AU) ?? this._$Cv;
  }
  constructor(e, t, s, r) {
    this.type = 2, this._$AH = p, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = s, this.options = r, this._$Cv = (r == null ? void 0 : r.isConnected) ?? !0;
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
    e = P(this, e, t), H(e) ? e === p || e == null || e === "" ? (this._$AH !== p && this._$AR(), this._$AH = p) : e !== this._$AH && e !== k && this._(e) : e._$litType$ !== void 0 ? this.$(e) : e.nodeType !== void 0 ? this.T(e) : Se(e) ? this.k(e) : this._(e);
  }
  O(e) {
    return this._$AA.parentNode.insertBefore(e, this._$AB);
  }
  T(e) {
    this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
  }
  _(e) {
    this._$AH !== p && H(this._$AH) ? this._$AA.nextSibling.data = e : this.T(E.createTextNode(e)), this._$AH = e;
  }
  $(e) {
    var a;
    const { values: t, _$litType$: s } = e, r = typeof s == "number" ? this._$AC(e) : (s.el === void 0 && (s.el = L.createElement(me(s.h, s.h[0]), this.options)), s);
    if (((a = this._$AH) == null ? void 0 : a._$AD) === r) this._$AH.p(t);
    else {
      const o = new Me(r, this), n = o.u(this.options);
      o.p(t), this.T(n), this._$AH = o;
    }
  }
  _$AC(e) {
    let t = le.get(e.strings);
    return t === void 0 && le.set(e.strings, t = new L(e)), t;
  }
  k(e) {
    Y(this._$AH) || (this._$AH = [], this._$AR());
    const t = this._$AH;
    let s, r = 0;
    for (const a of e) r === t.length ? t.push(s = new T(this.O(I()), this.O(I()), this, this.options)) : s = t[r], s._$AI(a), r++;
    r < t.length && (this._$AR(s && s._$AB.nextSibling, r), t.length = r);
  }
  _$AR(e = this._$AA.nextSibling, t) {
    var s;
    for ((s = this._$AP) == null ? void 0 : s.call(this, !1, !0, t); e !== this._$AB; ) {
      const r = e.nextSibling;
      e.remove(), e = r;
    }
  }
  setConnected(e) {
    var t;
    this._$AM === void 0 && (this._$Cv = e, (t = this._$AP) == null || t.call(this, e));
  }
}
class W {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(e, t, s, r, a) {
    this.type = 1, this._$AH = p, this._$AN = void 0, this.element = e, this.name = t, this._$AM = r, this.options = a, s.length > 2 || s[0] !== "" || s[1] !== "" ? (this._$AH = Array(s.length - 1).fill(new String()), this.strings = s) : this._$AH = p;
  }
  _$AI(e, t = this, s, r) {
    const a = this.strings;
    let o = !1;
    if (a === void 0) e = P(this, e, t, 0), o = !H(e) || e !== this._$AH && e !== k, o && (this._$AH = e);
    else {
      const n = e;
      let l, h;
      for (e = a[0], l = 0; l < a.length - 1; l++) h = P(this, n[s + l], t, l), h === k && (h = this._$AH[l]), o || (o = !H(h) || h !== this._$AH[l]), h === p ? e = p : e !== p && (e += (h ?? "") + a[l + 1]), this._$AH[l] = h;
    }
    o && !r && this.j(e);
  }
  j(e) {
    e === p ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
  }
}
class Ie extends W {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(e) {
    this.element[this.name] = e === p ? void 0 : e;
  }
}
class He extends W {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(e) {
    this.element.toggleAttribute(this.name, !!e && e !== p);
  }
}
class Le extends W {
  constructor(e, t, s, r, a) {
    super(e, t, s, r, a), this.type = 5;
  }
  _$AI(e, t = this) {
    if ((e = P(this, e, t, 0) ?? p) === k) return;
    const s = this._$AH, r = e === p && s !== p || e.capture !== s.capture || e.once !== s.once || e.passive !== s.passive, a = e !== p && (s === p || r);
    r && this.element.removeEventListener(this.name, this, s), a && this.element.addEventListener(this.name, this, e), this._$AH = e;
  }
  handleEvent(e) {
    var t;
    typeof this._$AH == "function" ? this._$AH.call(((t = this.options) == null ? void 0 : t.host) ?? this.element, e) : this._$AH.handleEvent(e);
  }
}
class Te {
  constructor(e, t, s) {
    this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = s;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(e) {
    P(this, e);
  }
}
const q = O.litHtmlPolyfillSupport;
q == null || q(L, T), (O.litHtmlVersions ?? (O.litHtmlVersions = [])).push("3.3.1");
const De = (i, e, t) => {
  const s = (t == null ? void 0 : t.renderBefore) ?? e;
  let r = s._$litPart$;
  if (r === void 0) {
    const a = (t == null ? void 0 : t.renderBefore) ?? null;
    s._$litPart$ = r = new T(e.insertBefore(I(), a), a, void 0, t ?? {});
  }
  return r._$AI(i), r;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const A = globalThis;
class M extends V {
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
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = De(t, this.renderRoot, this.renderOptions);
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
    return k;
  }
}
var he;
M._$litElement$ = !0, M.finalized = !0, (he = A.litElementHydrateSupport) == null || he.call(A, { LitElement: M });
const B = A.litElementPolyfillSupport;
B == null || B({ LitElement: M });
(A.litElementVersions ?? (A.litElementVersions = [])).push("4.2.1");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Ne = (i) => (e, t) => {
  t !== void 0 ? t.addInitializer(() => {
    customElements.define(i, e);
  }) : customElements.define(i, e);
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Ue = { attribute: !0, type: String, converter: z, reflect: !1, hasChanged: X }, ze = (i = Ue, e, t) => {
  const { kind: s, metadata: r } = t;
  let a = globalThis.litPropertyMetadata.get(r);
  if (a === void 0 && globalThis.litPropertyMetadata.set(r, a = /* @__PURE__ */ new Map()), s === "setter" && ((i = Object.create(i)).wrapped = !0), a.set(t.name, i), s === "accessor") {
    const { name: o } = t;
    return { set(n) {
      const l = e.get.call(this);
      e.set.call(this, n), this.requestUpdate(o, l, i);
    }, init(n) {
      return n !== void 0 && this.C(o, void 0, i, n), n;
    } };
  }
  if (s === "setter") {
    const { name: o } = t;
    return function(n) {
      const l = this[o];
      e.call(this, n), this.requestUpdate(o, l, i);
    };
  }
  throw Error("Unsupported decorator location: " + s);
};
function D(i) {
  return (e, t) => typeof t == "object" ? ze(i, e, t) : ((s, r, a) => {
    const o = r.hasOwnProperty(a);
    return r.constructor.createProperty(a, s), o ? Object.getOwnPropertyDescriptor(r, a) : void 0;
  })(i, e, t);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function m(i) {
  return D({ ...i, state: !0, attribute: !1 });
}
function Z(i) {
  if (!i || i.length !== 3) return "#000000";
  const [e, t, s] = i;
  return `#${[e, t, s].map((r) => Math.max(0, Math.min(255, r)).toString(16).padStart(2, "0")).join("")}`;
}
function je(i) {
  const e = i.trim();
  if (!e) return null;
  const t = e.match(/^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/);
  if (t) {
    let a = t[1];
    return a.length === 3 && (a = a[0] + a[0] + a[1] + a[1] + a[2] + a[2]), [
      parseInt(a.slice(0, 2), 16),
      parseInt(a.slice(2, 4), 16),
      parseInt(a.slice(4, 6), 16)
    ];
  }
  const s = e.match(/^(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})$/);
  if (s) {
    const a = Math.min(255, parseInt(s[1], 10)), o = Math.min(255, parseInt(s[2], 10)), n = Math.min(255, parseInt(s[3], 10));
    return [a, o, n];
  }
  const r = e.match(
    /^rgb\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/i
  );
  if (r) {
    const a = Math.min(255, parseInt(r[1], 10)), o = Math.min(255, parseInt(r[2], 10)), n = Math.min(255, parseInt(r[3], 10));
    return [a, o, n];
  }
  return null;
}
function G(i, e) {
  if (i.value !== void 0 && i.value !== null)
    return i.value;
  if (i.index !== void 0 && i.index !== null)
    return e[i.index];
}
function fe(i) {
  return Object.entries(i).map(([e, t]) => ({ value: e, label: t }));
}
function We(i, e) {
  return [{ value: "", label: i }, ...fe(e)];
}
var Re = Object.defineProperty, Fe = Object.getOwnPropertyDescriptor, g = (i, e, t, s) => {
  for (var r = s > 1 ? void 0 : s ? Fe(e, t) : e, a = i.length - 1, o; a >= 0; a--)
    (o = i[a]) && (r = (s ? o(e, t, r) : o(r)) || r);
  return s && r && Re(e, t, r), r;
};
const qe = (() => {
  try {
    return Intl.supportedValuesOf("timeZone");
  } catch {
    return [
      "UTC",
      "America/New_York",
      "America/Chicago",
      "America/Denver",
      "America/Los_Angeles",
      "Europe/London",
      "Europe/Paris",
      "Europe/Berlin",
      "Asia/Tokyo",
      "Asia/Shanghai",
      "Australia/Sydney"
    ];
  }
})(), b = { text: {} }, ce = { number: { mode: "box", step: "any" } }, de = /* @__PURE__ */ new WeakMap();
function Be(i) {
  let e = de.get(i);
  return e || (e = {
    number: { mode: "box", step: "any", min: i.min, max: i.max }
  }, de.set(i, e)), e;
}
function Ze(i, e) {
  let t;
  return (...s) => {
    clearTimeout(t), t = setTimeout(() => i(...s), e);
  };
}
let u = class extends M {
  constructor() {
    super(...arguments), this.narrow = !1, this._page = "main", this._config = null, this._views = [], this._devices = [], this._editingView = null, this._previewImage = null, this._previewLoading = !1, this._loading = !0, this._saving = !1, this._expandedItems = /* @__PURE__ */ new Set(), this._viewPreviews = /* @__PURE__ */ new Map(), this._createViewDialogOpen = !1, this._newViewName = "", this._creatingView = !1, this._createViewError = null, this._hexDrafts = /* @__PURE__ */ new Map(), this._refreshPreview = Ze(async () => {
      if (this._editingView) {
        this._previewLoading = !0;
        try {
          const i = await this.hass.connection.sendMessagePromise({
            type: "geekmagic/preview/render",
            view_config: {
              layout: this._editingView.layout,
              theme: this._editingView.theme,
              widgets: this._editingView.widgets
            }
          });
          this._previewImage = i.image;
        } catch (i) {
          console.error("Failed to render preview:", i);
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
      const [i, e, t] = await Promise.all([
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
      this._config = i, this._views = e.views, this._devices = t.devices, this._loadViewPreviews();
    } catch (i) {
      console.error("Failed to load GeekMagic config:", i);
    } finally {
      this._loading = !1;
    }
  }
  async _loadViewPreviews() {
    const i = this._views.map(async (s) => {
      try {
        const r = await this.hass.connection.sendMessagePromise({
          type: "geekmagic/preview/render",
          view_config: {
            layout: s.layout,
            theme: s.theme,
            widgets: s.widgets
          }
        });
        return { id: s.id, image: r.image };
      } catch (r) {
        return console.error(`Failed to load preview for view ${s.id}:`, r), { id: s.id, image: null };
      }
    }), e = await Promise.all(i), t = /* @__PURE__ */ new Map();
    for (const s of e)
      s.image && t.set(s.id, s.image);
    this._viewPreviews = t;
  }
  _suggestViewName() {
    const i = new Set(this._views.map((s) => s.name)), e = "New View";
    if (!i.has(e)) return e;
    let t = 2;
    for (; i.has(`${e} ${t}`); )
      t += 1;
    return `${e} ${t}`;
  }
  async _openCreateViewDialog() {
    var i;
    this._newViewName = this._suggestViewName(), this._createViewError = null, this._createViewDialogOpen = !0, await this.updateComplete, (i = this.renderRoot.querySelector(".create-view-name")) == null || i.focus();
  }
  _closeCreateViewDialog() {
    this._creatingView || (this._createViewDialogOpen = !1, this._createViewError = null);
  }
  _handleCreateViewDialogKeydown(i) {
    if (i.key === "Escape") {
      i.stopPropagation(), this._closeCreateViewDialog();
      return;
    }
    i.key === "Enter" && !i.shiftKey && (i.preventDefault(), this._createView());
  }
  async _createView() {
    const i = this._newViewName.trim();
    if (!(!i || this._creatingView)) {
      this._creatingView = !0, this._createViewError = null;
      try {
        const e = await this.hass.connection.sendMessagePromise({
          type: "geekmagic/views/create",
          name: i,
          layout: "grid_2x2",
          theme: "watchos",
          widgets: []
        });
        this._views = [...this._views, e.view], this._createViewDialogOpen = !1, this._newViewName = "", this._editView(e.view);
      } catch (e) {
        console.error("Failed to create view:", e), this._createViewError = "Could not create view. Check Home Assistant logs and try again.";
      } finally {
        this._creatingView = !1;
      }
    }
  }
  _editView(i) {
    this._editingView = { ...i, widgets: [...i.widgets] }, this._page = "editor", this._refreshPreview();
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
          (i) => i.id === this._editingView.id ? this._editingView : i
        ), this._page = "main", this._editingView = null, this._loadViewPreviews();
      } catch (i) {
        console.error("Failed to save view:", i);
      } finally {
        this._saving = !1;
      }
    }
  }
  async _deleteView(i) {
    if (confirm(`Delete view "${i.name}"?`))
      try {
        await this.hass.connection.sendMessagePromise({
          type: "geekmagic/views/delete",
          view_id: i.id
        }), this._views = this._views.filter((e) => e.id !== i.id);
      } catch (e) {
        console.error("Failed to delete view:", e);
      }
  }
  async _cloneView(i) {
    try {
      const e = await this.hass.connection.sendMessagePromise({
        type: "geekmagic/views/duplicate",
        view_id: i.id
      });
      this._views = [...this._views, e.view];
      try {
        const t = await this.hass.connection.sendMessagePromise({
          type: "geekmagic/preview/render",
          view_config: {
            layout: e.view.layout,
            theme: e.view.theme,
            widgets: e.view.widgets
          }
        });
        if (t.image) {
          const s = new Map(this._viewPreviews);
          s.set(e.view.id, t.image), this._viewPreviews = s;
        }
      } catch (t) {
        console.error(`Failed to load preview for view ${e.view.id}:`, t);
      }
    } catch (e) {
      console.error("Failed to clone view:", e);
    }
  }
  _updateEditingView(i) {
    this._editingView && (this._editingView = { ...this._editingView, ...i }, this._refreshPreview());
  }
  _updateWidget(i, e) {
    if (!this._editingView) return;
    if (e.type === "clock") {
      const r = Intl.DateTimeFormat().resolvedOptions().timeZone;
      e = {
        ...e,
        options: { ...e.options, timezone: r }
      };
    }
    const t = [...this._editingView.widgets], s = t.findIndex((r) => r.slot === i);
    s >= 0 ? t[s] = { ...t[s], ...e } : t.push({ slot: i, type: "", ...e }), this._editingView = { ...this._editingView, widgets: [...t] }, this.requestUpdate(), this._refreshPreview();
  }
  async _toggleDeviceView(i, e, t) {
    const s = t ? [...i.assigned_views, e] : i.assigned_views.filter((r) => r !== e);
    try {
      await this.hass.connection.sendMessagePromise({
        type: "geekmagic/devices/assign_views",
        entry_id: i.entry_id,
        view_ids: s
      }), this._devices = this._devices.map(
        (r) => r.entry_id === i.entry_id ? { ...r, assigned_views: s } : r
      );
    } catch (r) {
      console.error("Failed to update device views:", r);
    }
  }
  render() {
    return this._loading ? c`
        <div class="loading">
          <ha-spinner></ha-spinner>
        </div>
      ` : c`
      <div class="header">
        <ha-menu-button
          .hass=${this.hass}
          .narrow=${this.narrow}
        ></ha-menu-button>
        <ha-icon icon="mdi:monitor-dashboard"></ha-icon>
        <span class="header-title">GeekMagic</span>
      </div>
      <div class="content">${this._renderPage()}</div>
      ${this._renderCreateViewDialog()}
    `;
  }
  _renderPage() {
    switch (this._page) {
      case "main":
        return this._renderMain();
      case "editor":
        return this._renderEditor();
    }
  }
  _renderMain() {
    return c`
      <!-- Devices Section -->
      <div class="section">
        <h2 class="section-header">Devices</h2>
        ${this._devices.length === 0 ? c`
              <div class="empty-state-inline">
                <ha-icon icon="mdi:monitor-off"></ha-icon>
                <span>No devices configured. Add a device through Settings → Devices & Services.</span>
              </div>
            ` : c`
              <div class="devices-list">
                ${this._devices.map(
      (i) => c`
                    <ha-card>
                      <div class="card-content" style="padding-top: 16px;">
                        <div class="device-header">
                          <span class="device-name">${i.name}</span>
                          <span class="device-status ${i.online ? "online" : "offline"}">
                            <a href="http://${i.host}" target="_blank" rel="noopener noreferrer">${i.online ? "Online" : "Offline"}</a>
                          </span>
                        </div>
                        <div class="views-checkboxes">
                          ${this._views.length === 0 ? c`<p style="color: var(--secondary-text-color); margin: 8px 0 0;">
                                No views available. Create a view below.
                              </p>` : this._views.map(
        (e) => c`
                                  <label class="view-checkbox">
                                    <ha-checkbox
                                      .checked=${i.assigned_views.includes(e.id)}
                                      @change=${(t) => this._toggleDeviceView(
          i,
          e.id,
          t.target.checked
        )}
                                    ></ha-checkbox>
                                    ${e.name}
                                  </label>
                                `
      )}
                        </div>
                      </div>
                    </ha-card>
                  `
    )}
              </div>
            `}
      </div>

      <!-- Views Section -->
      <div class="section">
        <h2 class="section-header">Views</h2>
        <div class="views-grid">
          ${this._views.map(
      (i) => {
        var e, t, s;
        return c`
              <ha-card class="view-card" @click=${() => this._editView(i)}>
                <div class="view-card-content">
                  <div class="view-card-preview">
                    ${this._viewPreviews.has(i.id) ? c`<img
                          class="view-preview-image"
                          src="data:image/png;base64,${this._viewPreviews.get(i.id)}"
                          alt="${i.name}"
                        />` : c`<div class="view-preview-placeholder">
                          <ha-spinner size="small"></ha-spinner>
                        </div>`}
                  </div>
                  <div class="view-card-info">
                    <div class="view-card-header">
                      <h3>${i.name}</h3>
                      <div class="view-card-actions">
                        <ha-icon-button
                          .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                          title="Clone view"
                          @click=${(r) => {
          r.stopPropagation(), this._cloneView(i);
        }}
                        ></ha-icon-button>
                        <ha-icon-button
                          .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                          title="Delete view"
                          @click=${(r) => {
          r.stopPropagation(), this._deleteView(i);
        }}
                        ></ha-icon-button>
                      </div>
                    </div>
                    <div class="card-meta">
                      ${((t = (e = this._config) == null ? void 0 : e.layout_types[i.layout]) == null ? void 0 : t.name) || i.layout}
                      &bull; ${((s = this._config) == null ? void 0 : s.themes[i.theme]) || i.theme}
                      &bull; ${i.widgets.length} widgets
                    </div>
                  </div>
                </div>
              </ha-card>
            `;
      }
    )}
          <button
            class="add-card"
            type="button"
            @click=${() => this._openCreateViewDialog()}
          >
            <ha-icon icon="mdi:plus"></ha-icon>
            <span>Add View</span>
          </button>
        </div>
      </div>
    `;
  }
  _renderCreateViewDialog() {
    if (!this._createViewDialogOpen) return p;
    const i = this._newViewName.trim();
    return c`
      <div
        class="dialog-backdrop"
        @click=${() => this._closeCreateViewDialog()}
        @keydown=${(e) => this._handleCreateViewDialogKeydown(e)}
      >
        <ha-card
          class="dialog-card"
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-view-title"
          @click=${(e) => e.stopPropagation()}
        >
          <div class="dialog-content">
            <h2 id="create-view-title">Create View</h2>
            <p>Name the dashboard view before opening the editor.</p>
            <ha-selector
              class="create-view-name"
              .hass=${this.hass}
              .selector=${b}
              .required=${!1}
              .label=${"View name"}
              .value=${this._newViewName}
              @value-changed=${(e) => {
      this._newViewName = e.detail.value ?? "";
    }}
              @keydown=${(e) => this._handleCreateViewDialogKeydown(e)}
            ></ha-selector>
            ${this._createViewError ? c`<div class="dialog-error">${this._createViewError}</div>` : p}
            <div class="dialog-actions">
              <ha-button
                ?disabled=${this._creatingView}
                @click=${() => this._closeCreateViewDialog()}
              >
                Cancel
              </ha-button>
              <ha-button
                raised
                ?disabled=${!i || this._creatingView}
                @click=${() => this._createView()}
              >
                ${this._creatingView ? "Creating..." : "Create"}
              </ha-button>
            </div>
          </div>
        </ha-card>
      </div>
    `;
  }
  _renderEditor() {
    var e;
    if (!this._editingView || !this._config) return p;
    const i = ((e = this._config.layout_types[this._editingView.layout]) == null ? void 0 : e.slots) || 4;
    return c`
      <div class="editor-header">
        <ha-icon-button
          .path=${"M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z"}
          @click=${() => this._page = "main"}
        ></ha-icon-button>
        <ha-selector
          .hass=${this.hass}
          .selector=${b}
          .required=${!1}
          .value=${this._editingView.name}
          .placeholder=${"View name"}
          @value-changed=${(t) => this._updateEditingView({ name: t.detail.value ?? "" })}
        ></ha-selector>
        <ha-button raised ?disabled=${this._saving} @click=${this._saveView}>
          ${this._saving ? "Saving..." : "Save"}
        </ha-button>
      </div>

      <div class="editor-form">
        <!-- Preview at top -->
        <div class="preview-section">
          <ha-card class="preview-card">
            <div class="card-header">
              <h3>Preview</h3>
              <ha-icon-button
                .path=${"M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z"}
                @click=${() => this._refreshPreview()}
              ></ha-icon-button>
            </div>
            <div class="card-content">
              ${this._previewLoading ? c`<div class="preview-placeholder">
                    <ha-spinner></ha-spinner>
                  </div>` : this._previewImage ? c`<img
                      class="preview-image"
                      src="data:image/png;base64,${this._previewImage}"
                      alt="Preview"
                    />` : c`<div class="preview-placeholder">No preview</div>`}
            </div>
          </ha-card>
        </div>

        <!-- Layout picker -->
        <div class="layout-section">
          <span class="layout-section-label">Layout</span>
          <div class="layout-picker">
            ${Object.entries(this._config.layout_types).map(
      ([t, s]) => {
        var r;
        return c`
                <button
                  class="layout-option ${((r = this._editingView) == null ? void 0 : r.layout) === t ? "selected" : ""}"
                  @click=${() => this._updateEditingView({ layout: t })}
                  title="${s.name} (${s.slots} slots)"
                >
                  ${this._renderLayoutIcon(t)}
                </button>
              `;
      }
    )}
          </div>
        </div>

        <!-- Theme selector -->
        <div class="form-row">
          <ha-select
            label="Theme"
            .value=${this._editingView.theme}
            .options=${fe(this._config.themes)}
            @selected=${(t) => {
      const s = G(
        t.detail,
        Object.keys(this._config.themes)
      );
      s && this._updateEditingView({ theme: s });
    }}
            @closed=${(t) => t.stopPropagation()}
          >
            ${Object.entries(this._config.themes).map(
      ([t, s]) => c`
                <mwc-list-item value=${t}>${s}</mwc-list-item>
              `
    )}
          </ha-select>
        </div>

        <!-- Widget slots -->
        <div class="section-title">Widgets</div>
        <div class="slots-grid">
          ${Array.from(
      { length: i },
      (t, s) => this._renderSlotEditor(s, i)
    )}
        </div>
      </div>
    `;
  }
  _renderSlotEditor(i, e) {
    var o;
    if (!this._config || !this._editingView) return p;
    const t = this._editingView.widgets.find((n) => n.slot === i), s = (t == null ? void 0 : t.type) || "", r = this._config.widget_types[s], a = this._editingView.layout;
    return c`
      <ha-card class="slot-card">
        <div class="card-content">
          <div class="slot-header">
            ${this._renderPositionGrid(i, e, a)}
            <span style="flex: 1;">Slot ${i + 1}</span>
          </div>

          <div class="slot-field">
            <ha-select
              label="Widget Type"
              .value=${s}
              .options=${We(
      "-- Empty --",
      Object.fromEntries(
        Object.entries(this._config.widget_types).map(
          ([n, l]) => [n, l.name]
        )
      )
    )}
              @selected=${(n) => {
      const l = ["", ...Object.keys(this._config.widget_types)], h = G(n.detail, l) ?? "";
      this._updateWidget(i, { type: h });
    }}
              @closed=${(n) => n.stopPropagation()}
            >
              <mwc-list-item value="">-- Empty --</mwc-list-item>
              ${Object.entries(this._config.widget_types).map(
      ([n, l]) => c`
                  <mwc-list-item value=${n}>${l.name}</mwc-list-item>
                `
    )}
            </ha-select>
          </div>

          ${r != null && r.needs_entity ? c`
                <div class="slot-field">
                  <ha-selector
                    .hass=${this.hass}
                    .selector=${{
      entity: r.entity_domains ? { domain: r.entity_domains } : {}
    }}
                    .value=${(t == null ? void 0 : t.entity_id) || ""}
                    .label=${"Entity"}
                    @value-changed=${(n) => this._updateWidget(i, {
      entity_id: n.detail.value
    })}
                  ></ha-selector>
                </div>
              ` : p}

          <div class="slot-field">
            <ha-selector
              .hass=${this.hass}
              .selector=${b}
              .required=${!1}
              .label=${"Label (optional)"}
              .value=${(t == null ? void 0 : t.label) || ""}
              @value-changed=${(n) => this._updateWidget(i, { label: n.detail.value })}
            ></ha-selector>
          </div>

          ${(o = r == null ? void 0 : r.options) != null && o.length ? c`
                <div class="widget-options">
                  ${r.options.map(
      (n) => this._renderOptionField(i, t, n)
    )}
                </div>
              ` : p}
        </div>
      </ha-card>
    `;
  }
  _renderOptionField(i, e, t) {
    var r, a, o;
    const s = ((r = e == null ? void 0 : e.options) == null ? void 0 : r[t.key]) ?? t.default;
    switch (t.type) {
      case "boolean":
        return c`
          <div class="option-row">
            <label>${t.label}</label>
            <ha-switch
              .checked=${!!s}
              @change=${(n) => this._updateWidgetOption(
          i,
          t.key,
          n.target.checked
        )}
            ></ha-switch>
          </div>
        `;
      case "select":
        return c`
          <div class="option-field">
            <ha-select
              .label=${t.label}
              .value=${s || t.default || ""}
              .options=${t.options || []}
              @selected=${(n) => {
          const l = G(
            n.detail,
            t.options || []
          );
          l !== void 0 && this._updateWidgetOption(i, t.key, l);
        }}
              @closed=${(n) => n.stopPropagation()}
            >
              ${(a = t.options) == null ? void 0 : a.map(
          (n) => c`<mwc-list-item value=${n}>${n}</mwc-list-item>`
        )}
            </ha-select>
          </div>
        `;
      case "number":
        return c`
          <div class="option-field">
            <ha-selector
              .hass=${this.hass}
              .selector=${Be(t)}
              .required=${!1}
              .label=${t.label}
              .value=${(o = e == null ? void 0 : e.options) == null ? void 0 : o[t.key]}
              .placeholder=${t.default !== void 0 ? String(t.default) : ""}
              @value-changed=${(n) => this._updateWidgetOption(i, t.key, n.detail.value)}
            ></ha-selector>
          </div>
        `;
      case "text":
        return c`
          <div class="option-field">
            <ha-selector
              .hass=${this.hass}
              .selector=${b}
              .required=${!1}
              .label=${t.label}
              .value=${s || ""}
              .placeholder=${t.placeholder || ""}
              @value-changed=${(n) => this._updateWidgetOption(i, t.key, n.detail.value)}
            ></ha-selector>
          </div>
        `;
      case "textarea":
        return c`
          <div class="option-field option-textarea">
            <label>${t.label}</label>
            <textarea
              .value=${s || ""}
              placeholder=${t.placeholder || ""}
              spellcheck="false"
              @input=${(n) => this._updateWidgetOption(
          i,
          t.key,
          n.target.value
        )}
            ></textarea>
          </div>
        `;
      case "icon":
        return c`
          <div class="option-field">
            <ha-icon-picker
              .hass=${this.hass}
              .label=${t.label}
              .value=${s || ""}
              @value-changed=${(n) => this._updateWidgetOption(i, t.key, n.detail.value)}
            ></ha-icon-picker>
          </div>
        `;
      case "color":
        return c`
          <div class="option-field">
            <ha-selector
              .hass=${this.hass}
              .selector=${{ color_rgb: {} }}
              .value=${s}
              .label=${t.label}
              @value-changed=${(n) => this._updateWidgetOption(i, t.key, n.detail.value)}
            ></ha-selector>
            <div class="color-hex-input">
              <div
                class="color-preview-swatch"
                style="background-color: ${Z(s)}"
              ></div>
              ${this._renderHexField(
          `${i}-${t.key}`,
          s,
          "#FF5500 or 255,85,0",
          (n) => this._updateWidgetOption(i, t.key, n)
        )}
            </div>
          </div>
        `;
      case "entity":
        return c`
          <div class="option-field">
            <ha-selector
              .hass=${this.hass}
              .selector=${{ entity: {} }}
              .value=${s || ""}
              .label=${t.label}
              @value-changed=${(n) => this._updateWidgetOption(i, t.key, n.detail.value)}
            ></ha-selector>
          </div>
        `;
      case "thresholds":
        return this._renderThresholdsEditor(i, t.key, s);
      case "progress_items":
        return this._renderProgressItemsEditor(i, t.key, s);
      case "status_entities":
        return this._renderStatusEntitiesEditor(i, t.key, s);
      case "timezone":
        return c`
          <div class="option-field">
            <ha-combo-box
              .hass=${this.hass}
              .label=${t.label}
              .value=${s || ""}
              .items=${qe.map((n) => ({ value: n, label: n }))}
              item-value-path="value"
              item-label-path="label"
              allow-custom-value
              @value-changed=${(n) => this._updateWidgetOption(i, t.key, n.detail.value)}
            ></ha-combo-box>
          </div>
        `;
      default:
        return p;
    }
  }
  _updateWidgetOption(i, e, t) {
    if (!this._editingView) return;
    const s = [...this._editingView.widgets], r = s.findIndex((a) => a.slot === i);
    if (r >= 0) {
      const a = s[r];
      s[r] = {
        ...a,
        options: { ...a.options || {}, [e]: t }
      };
    } else
      s.push({
        slot: i,
        type: "",
        options: { [e]: t }
      });
    this._editingView = { ...this._editingView, widgets: [...s] }, this.requestUpdate(), this._refreshPreview();
  }
  _renderThresholdsEditor(i, e, t) {
    const s = t || [];
    return c`
      <div class="option-field">
        <div class="array-editor">
          <div class="array-editor-header">
            <span>Color Thresholds</span>
          </div>
          <div class="array-items">
            ${s.map(
      (r, a) => c`
                <div class="threshold-item-container">
                  <div class="threshold-item">
                    <ha-selector
                      class="threshold-value"
                      .hass=${this.hass}
                      .selector=${ce}
                      .required=${!1}
                      .label=${"Value"}
                      .value=${r.value}
                      @value-changed=${(o) => {
        const n = [...s];
        n[a] = { ...r, value: o.detail.value }, this._updateWidgetOption(i, e, n);
      }}
                    ></ha-selector>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ color_rgb: {} }}
                      .value=${r.color}
                      @value-changed=${(o) => {
        const n = [...s];
        n[a] = { ...r, color: o.detail.value }, this._updateWidgetOption(i, e, n);
      }}
                    ></ha-selector>
                    <ha-icon-button
                      .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                      @click=${() => {
        const o = s.filter((n, l) => l !== a);
        this._updateWidgetOption(i, e, o);
      }}
                    ></ha-icon-button>
                  </div>
                  <div class="threshold-hex-row">
                    <div
                      class="color-preview-swatch"
                      style="background-color: ${Z(r.color)}"
                    ></div>
                    ${this._renderHexField(
        `${i}-${e}-${a}`,
        r.color,
        "#FF5500",
        (o) => {
          const n = [...s];
          n[a] = { ...r, color: o }, this._updateWidgetOption(i, e, n);
        }
      )}
                  </div>
                </div>
              `
    )}
            <div
              class="add-item-button"
              @click=${() => {
      const r = [...s, { value: 0, color: [255, 255, 0] }];
      this._updateWidgetOption(i, e, r);
    }}
            >
              <ha-icon icon="mdi:plus"></ha-icon>
              Add Threshold
            </div>
          </div>
        </div>
      </div>
    `;
  }
  _renderProgressItemsEditor(i, e, t) {
    const s = t || [];
    return c`
      <div class="option-field">
        <div class="array-editor">
          <div class="array-editor-header">
            <span>Progress Items (${s.length})</span>
          </div>
          <div class="array-items">
            ${s.map((r, a) => {
      const o = `${i}-progress-${a}`, n = this._expandedItems.has(o);
      return c`
                <div class="array-item">
                  <div
                    class="array-item-header"
                    @click=${() => this._toggleItemExpanded(o)}
                  >
                    <span class="array-item-title">
                      ${r.label || r.entity_id || `Item ${a + 1}`}
                    </span>
                    <div class="array-item-actions">
                      <ha-icon-button
                        .path=${a > 0 ? "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z" : ""}
                        @click=${(l) => {
        l.stopPropagation(), a > 0 && this._moveArrayItem(i, e, s, a, -1);
      }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${a < s.length - 1 ? "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z" : ""}
                        @click=${(l) => {
        l.stopPropagation(), a < s.length - 1 && this._moveArrayItem(i, e, s, a, 1);
      }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                        @click=${(l) => {
        l.stopPropagation();
        const h = s.filter((v, d) => d !== a);
        this._updateWidgetOption(i, e, h);
      }}
                      ></ha-icon-button>
                    </div>
                  </div>
                  <div class="array-item-content ${n ? "" : "collapsed"}">
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ entity: {} }}
                      .value=${r.entity_id || ""}
                      .label=${"Entity"}
                      @value-changed=${(l) => this._updateArrayItem(i, e, s, a, {
        entity_id: l.detail.value
      })}
                    ></ha-selector>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${b}
                      .required=${!1}
                      .label=${"Label"}
                      .value=${r.label || ""}
                      @value-changed=${(l) => this._updateArrayItem(i, e, s, a, {
        label: l.detail.value
      })}
                    ></ha-selector>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${ce}
                      .required=${!1}
                      .label=${"Target"}
                      .placeholder=${"100"}
                      .value=${r.target}
                      @value-changed=${(l) => this._updateArrayItem(i, e, s, a, {
        target: l.detail.value
      })}
                    ></ha-selector>
                    <ha-icon-picker
                      .hass=${this.hass}
                      label="Icon"
                      .value=${r.icon || ""}
                      @value-changed=${(l) => this._updateArrayItem(i, e, s, a, {
        icon: l.detail.value
      })}
                    ></ha-icon-picker>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ color_rgb: {} }}
                      .value=${r.color}
                      .label=${"Color"}
                      @value-changed=${(l) => this._updateArrayItem(i, e, s, a, {
        color: l.detail.value
      })}
                    ></ha-selector>
                  </div>
                </div>
              `;
    })}
            <div
              class="add-item-button"
              @click=${() => {
      const r = [...s, { entity_id: "", target: 100 }];
      this._updateWidgetOption(i, e, r), this._expandedItems.add(`${i}-progress-${r.length - 1}`), this.requestUpdate();
    }}
            >
              <ha-icon icon="mdi:plus"></ha-icon>
              Add Progress Item
            </div>
          </div>
        </div>
      </div>
    `;
  }
  _renderStatusEntitiesEditor(i, e, t) {
    const s = t || [];
    return c`
      <div class="option-field">
        <div class="array-editor">
          <div class="array-editor-header">
            <span>Status Entities (${s.length})</span>
          </div>
          <div class="array-items">
            ${s.map((r, a) => {
      const o = `${i}-status-${a}`, n = this._expandedItems.has(o);
      return c`
                <div class="array-item">
                  <div
                    class="array-item-header"
                    @click=${() => this._toggleItemExpanded(o)}
                  >
                    <span class="array-item-title">
                      ${r.label || r.entity_id || `Entity ${a + 1}`}
                    </span>
                    <div class="array-item-actions">
                      <ha-icon-button
                        .path=${a > 0 ? "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z" : ""}
                        @click=${(l) => {
        l.stopPropagation(), a > 0 && this._moveArrayItem(i, e, s, a, -1);
      }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${a < s.length - 1 ? "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z" : ""}
                        @click=${(l) => {
        l.stopPropagation(), a < s.length - 1 && this._moveArrayItem(i, e, s, a, 1);
      }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                        @click=${(l) => {
        l.stopPropagation();
        const h = s.filter((v, d) => d !== a);
        this._updateWidgetOption(i, e, h);
      }}
                      ></ha-icon-button>
                    </div>
                  </div>
                  <div class="array-item-content ${n ? "" : "collapsed"}">
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ entity: {} }}
                      .value=${r.entity_id || ""}
                      .label=${"Entity"}
                      @value-changed=${(l) => this._updateArrayItem(i, e, s, a, {
        entity_id: l.detail.value
      })}
                    ></ha-selector>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${b}
                      .required=${!1}
                      .label=${"Label"}
                      .value=${r.label || ""}
                      @value-changed=${(l) => this._updateArrayItem(i, e, s, a, {
        label: l.detail.value
      })}
                    ></ha-selector>
                    <ha-icon-picker
                      .hass=${this.hass}
                      label="Icon"
                      .value=${r.icon || ""}
                      @value-changed=${(l) => this._updateArrayItem(i, e, s, a, {
        icon: l.detail.value
      })}
                    ></ha-icon-picker>
                  </div>
                </div>
              `;
    })}
            <div
              class="add-item-button"
              @click=${() => {
      const r = [...s, { entity_id: "" }];
      this._updateWidgetOption(i, e, r), this._expandedItems.add(`${i}-status-${r.length - 1}`), this.requestUpdate();
    }}
            >
              <ha-icon icon="mdi:plus"></ha-icon>
              Add Status Entity
            </div>
          </div>
        </div>
      </div>
    `;
  }
  /**
   * Hex/RGB text fallback for colour pickers (Safari). Commits on blur or
   * Enter like a native `change`, which does not escape ha-selector's
   * shadow roots; committing per keystroke would normalise a half-typed
   * "#FF5" to "#FFFF55" under the cursor.
   */
  _renderHexField(i, e, t, s) {
    const r = () => {
      const a = this._hexDrafts.get(i);
      this._hexDrafts.delete(i);
      const o = a === void 0 ? null : je(a);
      o && s(o);
    };
    return c`
      <ha-selector
        class="hex-input"
        .hass=${this.hass}
        .selector=${b}
        .required=${!1}
        .label=${"Hex (fallback)"}
        .placeholder=${t}
        .value=${Z(e)}
        @value-changed=${(a) => this._hexDrafts.set(i, a.detail.value ?? "")}
        @focusout=${r}
        @keydown=${(a) => {
      a.key === "Enter" && r();
    }}
      ></ha-selector>
    `;
  }
  _toggleItemExpanded(i) {
    this._expandedItems.has(i) ? this._expandedItems.delete(i) : this._expandedItems.add(i), this._expandedItems = new Set(this._expandedItems);
  }
  _updateArrayItem(i, e, t, s, r) {
    const a = [...t];
    a[s] = { ...a[s], ...r }, this._updateWidgetOption(i, e, a);
  }
  _moveArrayItem(i, e, t, s, r) {
    const a = s + r;
    if (a < 0 || a >= t.length) return;
    const o = [...t];
    [o[s], o[a]] = [o[a], o[s]], this._updateWidgetOption(i, e, o);
  }
  _renderPositionGrid(i, e, t) {
    let s = 2, r = !1;
    switch (t) {
      case "fullscreen":
        s = 1;
        break;
      case "grid_2x2":
        s = 2;
        break;
      case "grid_2x3":
        s = 3;
        break;
      case "grid_3x2":
        s = 2;
        break;
      case "hero":
        s = 3, r = !0;
        break;
      case "split":
        s = 2;
        break;
      case "three_column":
        s = 3;
        break;
      default:
        s = 2;
    }
    const a = [];
    if (r) {
      a.push(c`
        <div
          class="position-cell hero-main ${i === 0 ? "active" : ""}"
          @click=${() => this._swapSlots(i, 0)}
          title="Hero (main)"
        ></div>
      `);
      for (let o = 1; o <= 3; o++)
        a.push(c`
          <div
            class="position-cell ${i === o ? "active" : ""}"
            @click=${() => this._swapSlots(i, o)}
            title="Footer ${o}"
          ></div>
        `);
    } else
      for (let o = 0; o < e; o++)
        a.push(c`
          <div
            class="position-cell ${i === o ? "active" : ""}"
            @click=${() => this._swapSlots(i, o)}
            title="Slot ${o + 1}"
          ></div>
        `);
    return c`
      <div class="position-grid cols-${s}">${a}</div>
    `;
  }
  _renderLayoutIcon(i) {
    const t = {
      fullscreen: { cls: "full", cells: 1 },
      grid_2x2: { cls: "g-2x2", cells: 4 },
      grid_2x3: { cls: "g-2x3", cells: 6 },
      grid_3x2: { cls: "g-3x2", cells: 6 },
      grid_3x3: { cls: "g-3x3", cells: 9 },
      split_horizontal: { cls: "s-h", cells: 2 },
      split_vertical: { cls: "s-v", cells: 2 },
      split_h_1_2: { cls: "s-h-12", cells: 2 },
      split_h_2_1: { cls: "s-h-21", cells: 2 },
      three_column: { cls: "t-col", cells: 3 },
      three_row: { cls: "t-row", cells: 3 },
      hero: { cls: "hero", cells: 4 },
      hero_simple: { cls: "hero-simple", cells: 2 },
      sidebar_left: { cls: "sb-l", cells: 4 },
      sidebar_right: { cls: "sb-r", cells: 4 },
      hero_corner_tl: { cls: "hc-tl", cells: 6 },
      hero_corner_tr: { cls: "hc-tr", cells: 6 },
      hero_corner_bl: { cls: "hc-bl", cells: 6 },
      hero_corner_br: { cls: "hc-br", cells: 6 }
    }[i] || { cls: "", cells: 4 }, s = Array.from({ length: t.cells }, () => c`<div></div>`);
    return c`<div class="layout-icon ${t.cls}">${s}</div>`;
  }
  _swapSlots(i, e) {
    if (i === e || !this._editingView) return;
    const t = [...this._editingView.widgets], s = t.find((a) => a.slot === i), r = t.find((a) => a.slot === e);
    s && (s.slot = e), r && (r.slot = i), this._editingView = { ...this._editingView, widgets: [...t] }, this.requestUpdate(), this._refreshPreview();
  }
};
u.styles = $e`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      --mdc-theme-primary: var(--primary-color);
      --mdc-theme-on-primary: var(--text-primary-color);
    }

    /* Header */
    .header {
      display: flex;
      align-items: center;
      padding: 0 16px;
      height: 56px;
      border-bottom: 1px solid var(--divider-color);
      background: var(--app-header-background-color);
    }

    .header-title {
      font-size: 20px;
      font-weight: 400;
      margin-left: 8px;
    }

    .content {
      flex: 1;
      overflow: auto;
      padding: 16px;
      background: var(--primary-background-color);
    }

    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
    }

    /* ha-spinner ships with HA 2025.8+; older frontends get a CSS ring. */
    ha-spinner:not(:defined) {
      display: inline-block;
      box-sizing: border-box;
      width: 48px;
      height: 48px;
      border: 4px solid var(--divider-color);
      border-top-color: var(--primary-color);
      border-radius: 50%;
      animation: gm-spin 1s linear infinite;
    }

    ha-spinner[size="small"]:not(:defined) {
      width: 28px;
      height: 28px;
      border-width: 3px;
    }

    @keyframes gm-spin {
      to {
        transform: rotate(360deg);
      }
    }

    /* Views Grid */
    .views-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 16px;
    }

    ha-card {
      --ha-card-border-radius: 12px;
    }

    .view-card {
      cursor: pointer;
    }

    .view-card:hover {
      --ha-card-background: var(--secondary-background-color);
    }

    .view-card-content {
      display: flex;
      align-items: center;
      padding: 16px;
      gap: 16px;
    }

    .view-card-preview {
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      width: 80px;
      height: 80px;
      background: #000;
      border-radius: 8px;
    }

    .view-preview-image {
      width: 80px;
      height: 80px;
      border-radius: 8px;
      object-fit: contain;
    }

    .view-preview-placeholder {
      width: 80px;
      height: 80px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--secondary-text-color);
    }

    .view-card-info {
      flex: 1;
      min-width: 0;
    }

    .view-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 4px;
    }

    .view-card-actions {
      display: flex;
      align-items: center;
    }

    .view-card-header h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 500;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px;
    }

    .card-header h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 500;
    }

    .card-content {
      padding: 0 16px 16px;
    }

    .card-meta {
      font-size: 14px;
      color: var(--secondary-text-color);
    }

    .add-card {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 120px;
      width: 100%;
      font: inherit;
      background: transparent;
      border: 2px dashed var(--divider-color);
      border-radius: 12px;
      cursor: pointer;
      color: var(--secondary-text-color);
      transition: all 0.2s;
    }

    .add-card:hover {
      border-color: var(--primary-color);
      color: var(--primary-color);
    }

    .add-card:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }

    .dialog-backdrop {
      position: fixed;
      inset: 0;
      z-index: 10;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      background: rgba(0, 0, 0, 0.45);
    }

    .dialog-card {
      width: min(420px, 100%);
    }

    .dialog-content {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 20px;
    }

    .dialog-content h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 500;
      color: var(--primary-text-color);
    }

    .dialog-content p {
      margin: 0;
      color: var(--secondary-text-color);
      line-height: 1.4;
    }

    .dialog-error {
      color: var(--error-color);
      font-size: 14px;
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }

    /* Sections */
    .section {
      margin-bottom: 32px;
    }

    .section-header {
      font-size: 18px;
      font-weight: 500;
      margin: 0 0 16px 0;
      color: var(--primary-text-color);
    }

    .empty-state-inline {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px;
      color: var(--secondary-text-color);
      background: var(--card-background-color);
      border-radius: 12px;
    }

    /* Editor */
    .editor-header {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 24px;
    }

    .editor-header ha-selector {
      flex: 1;
    }

    .editor-form {
      width: 100%;
    }

    /* Preview section - above widgets */
    .preview-section {
      display: flex;
      flex-direction: column;
      align-items: center;
      margin-bottom: 24px;
    }

    .preview-card {
      width: 100%;
      max-width: 300px;
    }

    .preview-card .card-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
    }

    .preview-image {
      width: 200px;
      height: 200px;
      border-radius: 8px;
      background: #000;
      object-fit: contain;
    }

    .preview-placeholder {
      width: 200px;
      height: 200px;
      border-radius: 8px;
      background: var(--secondary-background-color);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--secondary-text-color);
    }

    /* Form Layout */
    .form-row {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;
    }

    .form-row > * {
      flex: 1;
    }

    .section-title {
      font-size: 14px;
      font-weight: 500;
      color: var(--primary-text-color);
      margin: 24px 0 16px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .section-title:first-child {
      margin-top: 0;
    }

    /* Slots list - fluid responsive grid */
    .slots-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
      width: 100%;
    }

    /* Single column on mobile */
    @media (max-width: 600px) {
      .slots-grid {
        grid-template-columns: 1fr;
      }
    }

    .slot-card {
      --ha-card-border-radius: 8px;
    }

    .slot-card .card-content {
      padding: 16px;
    }

    .slot-header {
      display: flex;
      align-items: center;
      font-weight: 500;
      margin-bottom: 16px;
      color: var(--primary-text-color);
    }

    /* Tiny position grid */
    .position-grid {
      display: inline-grid;
      gap: 2px;
      margin-right: 12px;
      padding: 4px;
      background: var(--secondary-background-color);
      border-radius: 4px;
    }

    .position-grid.cols-2 {
      grid-template-columns: repeat(2, 16px);
    }

    .position-grid.cols-3 {
      grid-template-columns: repeat(3, 16px);
    }

    .position-cell {
      width: 16px;
      height: 16px;
      background: var(--divider-color);
      border-radius: 2px;
      cursor: pointer;
      transition: all 0.15s;
    }

    .position-cell:hover {
      background: var(--primary-color);
      opacity: 0.7;
    }

    .position-cell.active {
      background: var(--primary-color);
    }

    .position-cell.hero-main {
      grid-column: 1 / -1;
      width: auto;
      height: 24px;
    }

    /* Layout Picker */
    .layout-section {
      margin-bottom: 16px;
    }

    .layout-section-label {
      font-size: 12px;
      font-weight: 500;
      color: var(--secondary-text-color);
      margin-bottom: 8px;
      display: block;
    }

    .layout-picker {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .layout-option {
      width: 48px;
      height: 48px;
      padding: 6px;
      border: 2px solid var(--divider-color);
      border-radius: 8px;
      background: var(--card-background-color);
      cursor: pointer;
      transition: all 0.15s;
    }

    .layout-option:hover {
      border-color: var(--primary-color);
    }

    .layout-option.selected {
      border-color: var(--primary-color);
      background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.1);
    }

    .layout-icon {
      width: 100%;
      height: 100%;
      display: grid;
      gap: 2px;
    }

    .layout-icon > div {
      background: var(--primary-text-color);
      opacity: 0.3;
      border-radius: 1px;
    }

    .layout-option.selected .layout-icon > div {
      opacity: 0.6;
    }

    /* Layout icon patterns */
    .layout-icon.full { grid-template: 1fr / 1fr; }
    .layout-icon.g-2x2 { grid-template: 1fr 1fr / 1fr 1fr; }
    .layout-icon.g-2x3 { grid-template: 1fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.g-3x2 { grid-template: 1fr 1fr 1fr / 1fr 1fr; }
    .layout-icon.g-3x3 { grid-template: 1fr 1fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.s-h { grid-template: 1fr / 1fr 1fr; }
    .layout-icon.s-v { grid-template: 1fr 1fr / 1fr; }
    .layout-icon.s-h-12 { grid-template: 1fr / 1fr 2fr; }
    .layout-icon.s-h-21 { grid-template: 1fr / 2fr 1fr; }
    .layout-icon.t-col { grid-template: 1fr / 1fr 1fr 1fr; }
    .layout-icon.t-row { grid-template: 1fr 1fr 1fr / 1fr; }
    .layout-icon.hero { grid-template: 2fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.hero > div:first-child { grid-column: 1 / -1; }
    .layout-icon.hero-simple { grid-template: 2fr 1fr / 1fr; }

    /* Sidebar layouts */
    .layout-icon.sb-l { grid-template: 1fr 1fr 1fr / 2fr 1fr; }
    .layout-icon.sb-l > div:first-child { grid-row: 1 / -1; }

    .layout-icon.sb-r { grid-template: 1fr 1fr 1fr / 1fr 2fr; }
    .layout-icon.sb-r > div:nth-child(4) { grid-row: 1 / -1; }

    /* Corner hero layouts - use 3x3 grid with 2x2 hero spanning */
    .layout-icon.hc-tl { grid-template: 1fr 1fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.hc-tl > div:first-child { grid-row: 1 / 3; grid-column: 1 / 3; }

    .layout-icon.hc-tr { grid-template: 1fr 1fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.hc-tr > div:nth-child(2) { grid-row: 1 / 3; grid-column: 2 / 4; }

    .layout-icon.hc-bl { grid-template: 1fr 1fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.hc-bl > div:nth-child(5) { grid-row: 2 / 4; grid-column: 1 / 3; }

    .layout-icon.hc-br { grid-template: 1fr 1fr 1fr / 1fr 1fr 1fr; }
    .layout-icon.hc-br > div:nth-child(5) { grid-row: 2 / 4; grid-column: 2 / 4; }

    .slot-field {
      margin-bottom: 16px;
    }

    .slot-field:last-child {
      margin-bottom: 0;
    }

    ha-select,
    ha-selector {
      display: block;
      width: 100%;
    }

    ha-entity-picker {
      display: block;
      width: 100%;
    }

    /* Widget options */
    .widget-options {
      border-top: 1px solid var(--divider-color);
      padding-top: 16px;
      margin-top: 16px;
    }

    .option-field {
      margin-bottom: 12px;
    }

    .option-field:last-child {
      margin-bottom: 0;
    }

    .option-textarea label {
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
      margin-bottom: 4px;
    }

    .option-textarea textarea {
      display: block;
      width: 100%;
      box-sizing: border-box;
      min-height: 140px;
      resize: vertical;
      font-family: var(--code-font-family, monospace);
      font-size: 12px;
      line-height: 1.4;
      color: var(--primary-text-color);
      background: var(--card-background-color);
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      padding: 8px;
    }

    .option-textarea textarea:focus {
      outline: none;
      border-color: var(--primary-color);
    }

    .option-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 0;
    }

    .option-row label {
      font-size: 14px;
      color: var(--primary-text-color);
    }

    /* Array editors */
    .array-editor {
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      padding: 12px;
      margin-top: 8px;
    }

    .array-editor-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }

    .array-editor-header span {
      font-size: 14px;
      font-weight: 500;
    }

    .array-items {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .array-item {
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      overflow: hidden;
    }

    .array-item-header {
      display: flex;
      align-items: center;
      padding: 8px 12px;
      background: var(--secondary-background-color);
      cursor: pointer;
    }

    .array-item-header:hover {
      background: var(--divider-color);
    }

    .array-item-title {
      flex: 1;
      font-size: 14px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .array-item-actions {
      display: flex;
      gap: 4px;
    }

    .array-item-content {
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .array-item-content.collapsed {
      display: none;
    }

    .add-item-button {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      padding: 8px;
      border: 1px dashed var(--divider-color);
      border-radius: 6px;
      cursor: pointer;
      color: var(--secondary-text-color);
      font-size: 14px;
      transition: all 0.2s;
    }

    .add-item-button:hover {
      border-color: var(--primary-color);
      color: var(--primary-color);
    }

    /* Color thresholds editor */
    .threshold-item-container {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 8px;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
    }

    .threshold-item {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .threshold-value {
      width: 80px;
    }

    .threshold-color {
      width: 60px;
      height: 32px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }

    .threshold-hex-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-left: 88px; /* Align with color picker (80px value + 8px gap) */
    }

    /* Color hex input fallback (Safari compatibility) */
    .color-hex-input {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 8px;
    }

    .color-hex-input .hex-input,
    .threshold-hex-row .hex-input {
      flex: 1;
    }

    .color-preview-swatch {
      width: 32px;
      height: 32px;
      border-radius: 4px;
      border: 1px solid var(--divider-color);
      flex-shrink: 0;
    }

    /* Devices */
    .devices-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
      max-width: 800px;
    }

    .device-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .device-name {
      font-size: 16px;
      font-weight: 500;
    }

    .device-status {
      font-size: 12px;
      padding: 4px 12px;
      border-radius: 12px;
      font-weight: 500;
    }

    .device-status.online {
      background: var(--success-color, #4caf50);
      color: white;
    }

    .device-status.offline {
      background: var(--error-color, #f44336);
      color: white;
    }

    .device-status a {
      color: inherit;
      text-decoration: none;
    }

    .views-checkboxes {
      margin-top: 16px;
    }

    .view-checkbox {
      display: flex;
      align-items: center;
      padding: 8px 0;
    }

    .view-checkbox ha-checkbox {
      margin-right: 8px;
    }

    /* Empty states */
    .empty-state {
      text-align: center;
      padding: 48px 16px;
      color: var(--secondary-text-color);
    }

    .empty-state ha-icon {
      --mdc-icon-size: 48px;
      margin-bottom: 16px;
      opacity: 0.5;
    }
  `;
g([
  D({ attribute: !1 })
], u.prototype, "hass", 2);
g([
  D({ type: Boolean })
], u.prototype, "narrow", 2);
g([
  D({ attribute: !1 })
], u.prototype, "route", 2);
g([
  D({ attribute: !1 })
], u.prototype, "panel", 2);
g([
  m()
], u.prototype, "_page", 2);
g([
  m()
], u.prototype, "_config", 2);
g([
  m()
], u.prototype, "_views", 2);
g([
  m()
], u.prototype, "_devices", 2);
g([
  m()
], u.prototype, "_editingView", 2);
g([
  m()
], u.prototype, "_previewImage", 2);
g([
  m()
], u.prototype, "_previewLoading", 2);
g([
  m()
], u.prototype, "_loading", 2);
g([
  m()
], u.prototype, "_saving", 2);
g([
  m()
], u.prototype, "_expandedItems", 2);
g([
  m()
], u.prototype, "_viewPreviews", 2);
g([
  m()
], u.prototype, "_createViewDialogOpen", 2);
g([
  m()
], u.prototype, "_newViewName", 2);
g([
  m()
], u.prototype, "_creatingView", 2);
g([
  m()
], u.prototype, "_createViewError", 2);
u = g([
  Ne("geekmagic-panel")
], u);
export {
  u as GeekMagicPanel
};
