/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const z = globalThis, J = z.ShadowRoot && (z.ShadyCSS === void 0 || z.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, X = Symbol(), ee = /* @__PURE__ */ new WeakMap();
let ue = class {
  constructor(e, t, r) {
    if (this._$cssResult$ = !0, r !== X) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = e, this.t = t;
  }
  get styleSheet() {
    let e = this.o;
    const t = this.t;
    if (J && e === void 0) {
      const r = t !== void 0 && t.length === 1;
      r && (e = ee.get(t)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), r && ee.set(t, e));
    }
    return e;
  }
  toString() {
    return this.cssText;
  }
};
const we = (i) => new ue(typeof i == "string" ? i : i + "", void 0, X), $e = (i, ...e) => {
  const t = i.length === 1 ? i[0] : e.reduce((r, s, a) => r + ((o) => {
    if (o._$cssResult$ === !0) return o.cssText;
    if (typeof o == "number") return o;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + o + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s) + i[a + 1], i[0]);
  return new ue(t, i, X);
}, ye = (i, e) => {
  if (J) i.adoptedStyleSheets = e.map((t) => t instanceof CSSStyleSheet ? t : t.styleSheet);
  else for (const t of e) {
    const r = document.createElement("style"), s = z.litNonce;
    s !== void 0 && r.setAttribute("nonce", s), r.textContent = t.cssText, i.appendChild(r);
  }
}, te = J ? (i) => i : (i) => i instanceof CSSStyleSheet ? ((e) => {
  let t = "";
  for (const r of e.cssRules) t += r.cssText;
  return we(t);
})(i) : i;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: be, defineProperty: xe, getOwnPropertyDescriptor: Ae, getOwnPropertyNames: Ee, getOwnPropertySymbols: Ve, getPrototypeOf: ke } = Object, $ = globalThis, ie = $.trustedTypes, Pe = ie ? ie.emptyScript : "", q = $.reactiveElementPolyfillSupport, O = (i, e) => i, j = { toAttribute(i, e) {
  switch (e) {
    case Boolean:
      i = i ? Pe : null;
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
} }, Y = (i, e) => !be(i, e), re = { attribute: !0, type: String, converter: j, reflect: !1, useDefault: !1, hasChanged: Y };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), $.litPropertyMetadata ?? ($.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let k = class extends HTMLElement {
  static addInitializer(e) {
    this._$Ei(), (this.l ?? (this.l = [])).push(e);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(e, t = re) {
    if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
      const r = Symbol(), s = this.getPropertyDescriptor(e, r, t);
      s !== void 0 && xe(this.prototype, e, s);
    }
  }
  static getPropertyDescriptor(e, t, r) {
    const { get: s, set: a } = Ae(this.prototype, e) ?? { get() {
      return this[t];
    }, set(o) {
      this[t] = o;
    } };
    return { get: s, set(o) {
      const n = s == null ? void 0 : s.call(this);
      a == null || a.call(this, o), this.requestUpdate(e, n, r);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(e) {
    return this.elementProperties.get(e) ?? re;
  }
  static _$Ei() {
    if (this.hasOwnProperty(O("elementProperties"))) return;
    const e = ke(this);
    e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(O("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(O("properties"))) {
      const t = this.properties, r = [...Ee(t), ...Ve(t)];
      for (const s of r) this.createProperty(s, t[s]);
    }
    const e = this[Symbol.metadata];
    if (e !== null) {
      const t = litPropertyMetadata.get(e);
      if (t !== void 0) for (const [r, s] of t) this.elementProperties.set(r, s);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t, r] of this.elementProperties) {
      const s = this._$Eu(t, r);
      s !== void 0 && this._$Eh.set(s, t);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(e) {
    const t = [];
    if (Array.isArray(e)) {
      const r = new Set(e.flat(1 / 0).reverse());
      for (const s of r) t.unshift(te(s));
    } else e !== void 0 && t.push(te(e));
    return t;
  }
  static _$Eu(e, t) {
    const r = t.attribute;
    return r === !1 ? void 0 : typeof r == "string" ? r : typeof e == "string" ? e.toLowerCase() : void 0;
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
    for (const r of t.keys()) this.hasOwnProperty(r) && (e.set(r, this[r]), delete this[r]);
    e.size > 0 && (this._$Ep = e);
  }
  createRenderRoot() {
    const e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return ye(e, this.constructor.elementStyles), e;
  }
  connectedCallback() {
    var e;
    this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this.enableUpdating(!0), (e = this._$EO) == null || e.forEach((t) => {
      var r;
      return (r = t.hostConnected) == null ? void 0 : r.call(t);
    });
  }
  enableUpdating(e) {
  }
  disconnectedCallback() {
    var e;
    (e = this._$EO) == null || e.forEach((t) => {
      var r;
      return (r = t.hostDisconnected) == null ? void 0 : r.call(t);
    });
  }
  attributeChangedCallback(e, t, r) {
    this._$AK(e, r);
  }
  _$ET(e, t) {
    var a;
    const r = this.constructor.elementProperties.get(e), s = this.constructor._$Eu(e, r);
    if (s !== void 0 && r.reflect === !0) {
      const o = (((a = r.converter) == null ? void 0 : a.toAttribute) !== void 0 ? r.converter : j).toAttribute(t, r.type);
      this._$Em = e, o == null ? this.removeAttribute(s) : this.setAttribute(s, o), this._$Em = null;
    }
  }
  _$AK(e, t) {
    var a, o;
    const r = this.constructor, s = r._$Eh.get(e);
    if (s !== void 0 && this._$Em !== s) {
      const n = r.getPropertyOptions(s), l = typeof n.converter == "function" ? { fromAttribute: n.converter } : ((a = n.converter) == null ? void 0 : a.fromAttribute) !== void 0 ? n.converter : j;
      this._$Em = s;
      const h = l.fromAttribute(t, n.type);
      this[s] = h ?? ((o = this._$Ej) == null ? void 0 : o.get(s)) ?? h, this._$Em = null;
    }
  }
  requestUpdate(e, t, r) {
    var s;
    if (e !== void 0) {
      const a = this.constructor, o = this[e];
      if (r ?? (r = a.getPropertyOptions(e)), !((r.hasChanged ?? Y)(o, t) || r.useDefault && r.reflect && o === ((s = this._$Ej) == null ? void 0 : s.get(e)) && !this.hasAttribute(a._$Eu(e, r)))) return;
      this.C(e, t, r);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(e, t, { useDefault: r, reflect: s, wrapped: a }, o) {
    r && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(e) && (this._$Ej.set(e, o ?? t ?? this[e]), a !== !0 || o !== void 0) || (this._$AL.has(e) || (this.hasUpdated || r || (t = void 0), this._$AL.set(e, t)), s === !0 && this._$Em !== e && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(e));
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
    var r;
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this._$Ep) {
        for (const [a, o] of this._$Ep) this[a] = o;
        this._$Ep = void 0;
      }
      const s = this.constructor.elementProperties;
      if (s.size > 0) for (const [a, o] of s) {
        const { wrapped: n } = o, l = this[a];
        n !== !0 || this._$AL.has(a) || l === void 0 || this.C(a, void 0, o, l);
      }
    }
    let e = !1;
    const t = this._$AL;
    try {
      e = this.shouldUpdate(t), e ? (this.willUpdate(t), (r = this._$EO) == null || r.forEach((s) => {
        var a;
        return (a = s.hostUpdate) == null ? void 0 : a.call(s);
      }), this.update(t)) : this._$EM();
    } catch (s) {
      throw e = !1, this._$EM(), s;
    }
    e && this._$AE(t);
  }
  willUpdate(e) {
  }
  _$AE(e) {
    var t;
    (t = this._$EO) == null || t.forEach((r) => {
      var s;
      return (s = r.hostUpdated) == null ? void 0 : s.call(r);
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
k.elementStyles = [], k.shadowRootOptions = { mode: "open" }, k[O("elementProperties")] = /* @__PURE__ */ new Map(), k[O("finalized")] = /* @__PURE__ */ new Map(), q == null || q({ ReactiveElement: k }), ($.reactiveElementVersions ?? ($.reactiveElementVersions = [])).push("2.1.1");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const M = globalThis, R = M.trustedTypes, se = R ? R.createPolicy("lit-html", { createHTML: (i) => i }) : void 0, ge = "$lit$", w = `lit$${Math.random().toFixed(9).slice(2)}$`, ve = "?" + w, Se = `<${ve}>`, E = document, H = () => E.createComment(""), L = (i) => i === null || typeof i != "object" && typeof i != "function", Q = Array.isArray, Ce = (i) => Q(i) || typeof (i == null ? void 0 : i[Symbol.iterator]) == "function", F = `[ 	
\f\r]`, C = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, ae = /-->/g, oe = />/g, y = RegExp(`>|${F}(?:([^\\s"'>=/]+)(${F}*=${F}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), ne = /'/g, le = /"/g, fe = /^(?:script|style|textarea|title)$/i, Oe = (i) => (e, ...t) => ({ _$litType$: i, strings: e, values: t }), c = Oe(1), P = Symbol.for("lit-noChange"), p = Symbol.for("lit-nothing"), ce = /* @__PURE__ */ new WeakMap(), x = E.createTreeWalker(E, 129);
function me(i, e) {
  if (!Q(i) || !i.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return se !== void 0 ? se.createHTML(e) : e;
}
const Me = (i, e) => {
  const t = i.length - 1, r = [];
  let s, a = e === 2 ? "<svg>" : e === 3 ? "<math>" : "", o = C;
  for (let n = 0; n < t; n++) {
    const l = i[n];
    let h, v, d = -1, m = 0;
    for (; m < l.length && (o.lastIndex = m, v = o.exec(l), v !== null); ) m = o.lastIndex, o === C ? v[1] === "!--" ? o = ae : v[1] !== void 0 ? o = oe : v[2] !== void 0 ? (fe.test(v[2]) && (s = RegExp("</" + v[2], "g")), o = y) : v[3] !== void 0 && (o = y) : o === y ? v[0] === ">" ? (o = s ?? C, d = -1) : v[1] === void 0 ? d = -2 : (d = o.lastIndex - v[2].length, h = v[1], o = v[3] === void 0 ? y : v[3] === '"' ? le : ne) : o === le || o === ne ? o = y : o === ae || o === oe ? o = C : (o = y, s = void 0);
    const _ = o === y && i[n + 1].startsWith("/>") ? " " : "";
    a += o === C ? l + Se : d >= 0 ? (r.push(h), l.slice(0, d) + ge + l.slice(d) + w + _) : l + w + (d === -2 ? n : _);
  }
  return [me(i, a + (i[t] || "<?>") + (e === 2 ? "</svg>" : e === 3 ? "</math>" : "")), r];
};
class T {
  constructor({ strings: e, _$litType$: t }, r) {
    let s;
    this.parts = [];
    let a = 0, o = 0;
    const n = e.length - 1, l = this.parts, [h, v] = Me(e, t);
    if (this.el = T.createElement(h, r), x.currentNode = this.el.content, t === 2 || t === 3) {
      const d = this.el.content.firstChild;
      d.replaceWith(...d.childNodes);
    }
    for (; (s = x.nextNode()) !== null && l.length < n; ) {
      if (s.nodeType === 1) {
        if (s.hasAttributes()) for (const d of s.getAttributeNames()) if (d.endsWith(ge)) {
          const m = v[o++], _ = s.getAttribute(d).split(w), U = /([.?@])?(.*)/.exec(m);
          l.push({ type: 1, index: a, name: U[2], strings: _, ctor: U[1] === "." ? He : U[1] === "?" ? Le : U[1] === "@" ? Te : W }), s.removeAttribute(d);
        } else d.startsWith(w) && (l.push({ type: 6, index: a }), s.removeAttribute(d));
        if (fe.test(s.tagName)) {
          const d = s.textContent.split(w), m = d.length - 1;
          if (m > 0) {
            s.textContent = R ? R.emptyScript : "";
            for (let _ = 0; _ < m; _++) s.append(d[_], H()), x.nextNode(), l.push({ type: 2, index: ++a });
            s.append(d[m], H());
          }
        }
      } else if (s.nodeType === 8) if (s.data === ve) l.push({ type: 2, index: a });
      else {
        let d = -1;
        for (; (d = s.data.indexOf(w, d + 1)) !== -1; ) l.push({ type: 7, index: a }), d += w.length - 1;
      }
      a++;
    }
  }
  static createElement(e, t) {
    const r = E.createElement("template");
    return r.innerHTML = e, r;
  }
}
function S(i, e, t = i, r) {
  var o, n;
  if (e === P) return e;
  let s = r !== void 0 ? (o = t._$Co) == null ? void 0 : o[r] : t._$Cl;
  const a = L(e) ? void 0 : e._$litDirective$;
  return (s == null ? void 0 : s.constructor) !== a && ((n = s == null ? void 0 : s._$AO) == null || n.call(s, !1), a === void 0 ? s = void 0 : (s = new a(i), s._$AT(i, t, r)), r !== void 0 ? (t._$Co ?? (t._$Co = []))[r] = s : t._$Cl = s), s !== void 0 && (e = S(i, s._$AS(i, e.values), s, r)), e;
}
class Ie {
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
    const { el: { content: t }, parts: r } = this._$AD, s = ((e == null ? void 0 : e.creationScope) ?? E).importNode(t, !0);
    x.currentNode = s;
    let a = x.nextNode(), o = 0, n = 0, l = r[0];
    for (; l !== void 0; ) {
      if (o === l.index) {
        let h;
        l.type === 2 ? h = new D(a, a.nextSibling, this, e) : l.type === 1 ? h = new l.ctor(a, l.name, l.strings, this, e) : l.type === 6 && (h = new De(a, this, e)), this._$AV.push(h), l = r[++n];
      }
      o !== (l == null ? void 0 : l.index) && (a = x.nextNode(), o++);
    }
    return x.currentNode = E, s;
  }
  p(e) {
    let t = 0;
    for (const r of this._$AV) r !== void 0 && (r.strings !== void 0 ? (r._$AI(e, r, t), t += r.strings.length - 2) : r._$AI(e[t])), t++;
  }
}
class D {
  get _$AU() {
    var e;
    return ((e = this._$AM) == null ? void 0 : e._$AU) ?? this._$Cv;
  }
  constructor(e, t, r, s) {
    this.type = 2, this._$AH = p, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = r, this.options = s, this._$Cv = (s == null ? void 0 : s.isConnected) ?? !0;
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
    e = S(this, e, t), L(e) ? e === p || e == null || e === "" ? (this._$AH !== p && this._$AR(), this._$AH = p) : e !== this._$AH && e !== P && this._(e) : e._$litType$ !== void 0 ? this.$(e) : e.nodeType !== void 0 ? this.T(e) : Ce(e) ? this.k(e) : this._(e);
  }
  O(e) {
    return this._$AA.parentNode.insertBefore(e, this._$AB);
  }
  T(e) {
    this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
  }
  _(e) {
    this._$AH !== p && L(this._$AH) ? this._$AA.nextSibling.data = e : this.T(E.createTextNode(e)), this._$AH = e;
  }
  $(e) {
    var a;
    const { values: t, _$litType$: r } = e, s = typeof r == "number" ? this._$AC(e) : (r.el === void 0 && (r.el = T.createElement(me(r.h, r.h[0]), this.options)), r);
    if (((a = this._$AH) == null ? void 0 : a._$AD) === s) this._$AH.p(t);
    else {
      const o = new Ie(s, this), n = o.u(this.options);
      o.p(t), this.T(n), this._$AH = o;
    }
  }
  _$AC(e) {
    let t = ce.get(e.strings);
    return t === void 0 && ce.set(e.strings, t = new T(e)), t;
  }
  k(e) {
    Q(this._$AH) || (this._$AH = [], this._$AR());
    const t = this._$AH;
    let r, s = 0;
    for (const a of e) s === t.length ? t.push(r = new D(this.O(H()), this.O(H()), this, this.options)) : r = t[s], r._$AI(a), s++;
    s < t.length && (this._$AR(r && r._$AB.nextSibling, s), t.length = s);
  }
  _$AR(e = this._$AA.nextSibling, t) {
    var r;
    for ((r = this._$AP) == null ? void 0 : r.call(this, !1, !0, t); e !== this._$AB; ) {
      const s = e.nextSibling;
      e.remove(), e = s;
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
  constructor(e, t, r, s, a) {
    this.type = 1, this._$AH = p, this._$AN = void 0, this.element = e, this.name = t, this._$AM = s, this.options = a, r.length > 2 || r[0] !== "" || r[1] !== "" ? (this._$AH = Array(r.length - 1).fill(new String()), this.strings = r) : this._$AH = p;
  }
  _$AI(e, t = this, r, s) {
    const a = this.strings;
    let o = !1;
    if (a === void 0) e = S(this, e, t, 0), o = !L(e) || e !== this._$AH && e !== P, o && (this._$AH = e);
    else {
      const n = e;
      let l, h;
      for (e = a[0], l = 0; l < a.length - 1; l++) h = S(this, n[r + l], t, l), h === P && (h = this._$AH[l]), o || (o = !L(h) || h !== this._$AH[l]), h === p ? e = p : e !== p && (e += (h ?? "") + a[l + 1]), this._$AH[l] = h;
    }
    o && !s && this.j(e);
  }
  j(e) {
    e === p ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
  }
}
class He extends W {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(e) {
    this.element[this.name] = e === p ? void 0 : e;
  }
}
class Le extends W {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(e) {
    this.element.toggleAttribute(this.name, !!e && e !== p);
  }
}
class Te extends W {
  constructor(e, t, r, s, a) {
    super(e, t, r, s, a), this.type = 5;
  }
  _$AI(e, t = this) {
    if ((e = S(this, e, t, 0) ?? p) === P) return;
    const r = this._$AH, s = e === p && r !== p || e.capture !== r.capture || e.once !== r.once || e.passive !== r.passive, a = e !== p && (r === p || s);
    s && this.element.removeEventListener(this.name, this, r), a && this.element.addEventListener(this.name, this, e), this._$AH = e;
  }
  handleEvent(e) {
    var t;
    typeof this._$AH == "function" ? this._$AH.call(((t = this.options) == null ? void 0 : t.host) ?? this.element, e) : this._$AH.handleEvent(e);
  }
}
class De {
  constructor(e, t, r) {
    this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = r;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(e) {
    S(this, e);
  }
}
const Z = M.litHtmlPolyfillSupport;
Z == null || Z(T, D), (M.litHtmlVersions ?? (M.litHtmlVersions = [])).push("3.3.1");
const Ne = (i, e, t) => {
  const r = (t == null ? void 0 : t.renderBefore) ?? e;
  let s = r._$litPart$;
  if (s === void 0) {
    const a = (t == null ? void 0 : t.renderBefore) ?? null;
    r._$litPart$ = s = new D(e.insertBefore(H(), a), a, void 0, t ?? {});
  }
  return s._$AI(i), s;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const A = globalThis;
class I extends k {
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
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Ne(t, this.renderRoot, this.renderOptions);
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
    return P;
  }
}
var pe;
I._$litElement$ = !0, I.finalized = !0, (pe = A.litElementHydrateSupport) == null || pe.call(A, { LitElement: I });
const B = A.litElementPolyfillSupport;
B == null || B({ LitElement: I });
(A.litElementVersions ?? (A.litElementVersions = [])).push("4.2.1");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Ue = (i) => (e, t) => {
  t !== void 0 ? t.addInitializer(() => {
    customElements.define(i, e);
  }) : customElements.define(i, e);
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const ze = { attribute: !0, type: String, converter: j, reflect: !1, hasChanged: Y }, je = (i = ze, e, t) => {
  const { kind: r, metadata: s } = t;
  let a = globalThis.litPropertyMetadata.get(s);
  if (a === void 0 && globalThis.litPropertyMetadata.set(s, a = /* @__PURE__ */ new Map()), r === "setter" && ((i = Object.create(i)).wrapped = !0), a.set(t.name, i), r === "accessor") {
    const { name: o } = t;
    return { set(n) {
      const l = e.get.call(this);
      e.set.call(this, n), this.requestUpdate(o, l, i);
    }, init(n) {
      return n !== void 0 && this.C(o, void 0, i, n), n;
    } };
  }
  if (r === "setter") {
    const { name: o } = t;
    return function(n) {
      const l = this[o];
      e.call(this, n), this.requestUpdate(o, l, i);
    };
  }
  throw Error("Unsupported decorator location: " + r);
};
function N(i) {
  return (e, t) => typeof t == "object" ? je(i, e, t) : ((r, s, a) => {
    const o = s.hasOwnProperty(a);
    return s.constructor.createProperty(a, r), o ? Object.getOwnPropertyDescriptor(s, a) : void 0;
  })(i, e, t);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function f(i) {
  return N({ ...i, state: !0, attribute: !1 });
}
function G(i) {
  if (!i || i.length !== 3) return "#000000";
  const [e, t, r] = i;
  return `#${[e, t, r].map((s) => Math.max(0, Math.min(255, s)).toString(16).padStart(2, "0")).join("")}`;
}
function Re(i) {
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
  const r = e.match(/^(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})$/);
  if (r) {
    const a = Math.min(255, parseInt(r[1], 10)), o = Math.min(255, parseInt(r[2], 10)), n = Math.min(255, parseInt(r[3], 10));
    return [a, o, n];
  }
  const s = e.match(
    /^rgb\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/i
  );
  if (s) {
    const a = Math.min(255, parseInt(s[1], 10)), o = Math.min(255, parseInt(s[2], 10)), n = Math.min(255, parseInt(s[3], 10));
    return [a, o, n];
  }
  return null;
}
function We(i) {
  return structuredClone(i);
}
function qe(i, e, t) {
  return e === t ? i : i.map((r) => r.slot === e ? { ...r, slot: t } : r.slot === t ? { ...r, slot: e } : r);
}
class Fe {
  constructor() {
    this._latest = 0;
  }
  /** Start a request, invalidating every earlier token. */
  next() {
    return this._latest += 1, this._latest;
  }
  /** Invalidate in-flight requests without starting a new one. */
  cancel() {
    this._latest += 1;
  }
  isCurrent(e) {
    return e === this._latest;
  }
}
function V(i) {
  if (typeof i == "string" && i) return i;
  if (i && typeof i == "object" && "message" in i) {
    const e = i.message;
    if (typeof e == "string" && e) return e;
  }
  return "Unknown error";
}
function K(i, e) {
  if (i.value !== void 0 && i.value !== null)
    return i.value;
  if (i.index !== void 0 && i.index !== null)
    return e[i.index];
}
function _e(i) {
  return Object.entries(i).map(([e, t]) => ({ value: e, label: t }));
}
function Ze(i, e) {
  return [{ value: "", label: i }, ..._e(e)];
}
var Be = Object.defineProperty, Ge = Object.getOwnPropertyDescriptor, g = (i, e, t, r) => {
  for (var s = r > 1 ? void 0 : r ? Ge(e, t) : e, a = i.length - 1, o; a >= 0; a--)
    (o = i[a]) && (s = (r ? o(e, t, s) : o(s)) || s);
  return r && s && Be(e, t, s), s;
};
const Ke = (() => {
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
})(), b = { text: {} }, de = { number: { mode: "box", step: "any" } }, he = /* @__PURE__ */ new WeakMap();
function Je(i) {
  let e = he.get(i);
  return e || (e = {
    number: { mode: "box", step: "any", min: i.min, max: i.max }
  }, he.set(i, e)), e;
}
const Xe = {
  select: { options: Ke, custom_value: !0, mode: "dropdown" }
};
function Ye(i, e) {
  let t;
  return (...r) => {
    clearTimeout(t), t = setTimeout(() => i(...r), e);
  };
}
let u = class extends I {
  constructor() {
    super(...arguments), this.narrow = !1, this._page = "main", this._config = null, this._views = [], this._devices = [], this._editingView = null, this._previewImage = null, this._previewLoading = !1, this._previewError = null, this._previewSeq = new Fe(), this._loading = !0, this._loadError = null, this._actionError = null, this._saving = !1, this._expandedItems = /* @__PURE__ */ new Set(), this._viewPreviews = /* @__PURE__ */ new Map(), this._createViewDialogOpen = !1, this._newViewName = "", this._creatingView = !1, this._createViewError = null, this._hexDrafts = /* @__PURE__ */ new Map(), this._refreshPreview = Ye(async () => {
      if (!this._editingView) return;
      const i = this._previewSeq.next();
      this._previewLoading = !0;
      try {
        const e = await this.hass.connection.sendMessagePromise({
          type: "geekmagic/preview/render",
          view_config: {
            layout: this._editingView.layout,
            theme: this._editingView.theme,
            widgets: this._editingView.widgets
          }
        });
        if (!this._previewSeq.isCurrent(i)) return;
        this._previewImage = e.image, this._previewError = null;
      } catch (e) {
        if (!this._previewSeq.isCurrent(i)) return;
        console.error("Failed to render preview:", e), this._previewError = V(e);
      } finally {
        this._previewSeq.isCurrent(i) && (this._previewLoading = !1);
      }
    }, 500);
  }
  firstUpdated() {
    this._loadData();
  }
  async _loadData() {
    this._loading = !0, this._loadError = null;
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
      console.error("Failed to load GeekMagic config:", i), this._loadError = V(i);
    } finally {
      this._loading = !1;
    }
  }
  async _loadViewPreviews() {
    const i = this._views.map(async (r) => {
      try {
        const s = await this.hass.connection.sendMessagePromise({
          type: "geekmagic/preview/render",
          view_config: {
            layout: r.layout,
            theme: r.theme,
            widgets: r.widgets
          }
        });
        return { id: r.id, image: s.image };
      } catch (s) {
        return console.error(`Failed to load preview for view ${r.id}:`, s), { id: r.id, image: null };
      }
    }), e = await Promise.all(i), t = /* @__PURE__ */ new Map();
    for (const r of e)
      r.image && t.set(r.id, r.image);
    this._viewPreviews = t;
  }
  _suggestViewName() {
    const i = new Set(this._views.map((r) => r.name)), e = "New View";
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
    this._editingView = We(i), this._page = "editor", this._actionError = null, this._previewSeq.cancel(), this._previewImage = null, this._previewError = null, this._previewLoading = !1, this._refreshPreview();
  }
  async _saveView() {
    if (this._editingView) {
      this._saving = !0, this._actionError = null;
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
        console.error("Failed to save view:", i), this._actionError = `Could not save view: ${V(i)}`;
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
        console.error("Failed to delete view:", e), this._actionError = `Could not delete view: ${V(e)}`;
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
          const r = new Map(this._viewPreviews);
          r.set(e.view.id, t.image), this._viewPreviews = r;
        }
      } catch (t) {
        console.error(`Failed to load preview for view ${e.view.id}:`, t);
      }
    } catch (e) {
      console.error("Failed to clone view:", e), this._actionError = `Could not clone view: ${V(e)}`;
    }
  }
  _updateEditingView(i) {
    this._editingView && (this._editingView = { ...this._editingView, ...i }, this._refreshPreview());
  }
  _renameEditingView(i) {
    this._editingView && (this._editingView = { ...this._editingView, name: i });
  }
  _updateWidget(i, e) {
    if (!this._editingView) return;
    if (e.type === "clock") {
      const s = Intl.DateTimeFormat().resolvedOptions().timeZone;
      e = {
        ...e,
        options: { ...e.options, timezone: s }
      };
    }
    const t = [...this._editingView.widgets], r = t.findIndex((s) => s.slot === i);
    r >= 0 ? t[r] = { ...t[r], ...e } : t.push({ slot: i, type: "", ...e }), this._editingView = { ...this._editingView, widgets: [...t] }, this.requestUpdate(), this._refreshPreview();
  }
  async _toggleDeviceView(i, e, t) {
    const r = t ? [...i.assigned_views, e] : i.assigned_views.filter((s) => s !== e);
    try {
      await this.hass.connection.sendMessagePromise({
        type: "geekmagic/devices/assign_views",
        entry_id: i.entry_id,
        view_ids: r
      }), this._devices = this._devices.map(
        (s) => s.entry_id === i.entry_id ? { ...s, assigned_views: r } : s
      );
    } catch (s) {
      console.error("Failed to update device views:", s), this._actionError = `Could not update device views: ${V(s)}`;
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
      <div class="content">
        ${this._loadError ? c`
              <ha-alert alert-type="error">
                Could not load GeekMagic data: ${this._loadError}
                <ha-button slot="action" @click=${() => this._loadData()}>
                  Retry
                </ha-button>
              </ha-alert>
            ` : c`${this._renderActionError()}${this._renderPage()}`}
      </div>
      ${this._renderCreateViewDialog()}
    `;
  }
  _renderActionError() {
    return this._actionError ? c`
      <ha-alert class="action-error" alert-type="error">
        ${this._actionError}
        <ha-button slot="action" @click=${() => this._actionError = null}>
          Dismiss
        </ha-button>
      </ha-alert>
    ` : p;
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
        var e, t, r;
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
                          @click=${(s) => {
          s.stopPropagation(), this._cloneView(i);
        }}
                        ></ha-icon-button>
                        <ha-icon-button
                          .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                          title="Delete view"
                          @click=${(s) => {
          s.stopPropagation(), this._deleteView(i);
        }}
                        ></ha-icon-button>
                      </div>
                    </div>
                    <div class="card-meta">
                      ${((t = (e = this._config) == null ? void 0 : e.layout_types[i.layout]) == null ? void 0 : t.name) || i.layout}
                      &bull; ${((r = this._config) == null ? void 0 : r.themes[i.theme]) || i.theme}
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
          @value-changed=${(t) => this._renameEditingView(t.detail.value ?? "")}
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
                  </div>` : this._previewError ? c`<div class="preview-placeholder preview-error">
                      Preview failed: ${this._previewError}
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
      ([t, r]) => {
        var s;
        return c`
                <button
                  class="layout-option ${((s = this._editingView) == null ? void 0 : s.layout) === t ? "selected" : ""}"
                  @click=${() => this._updateEditingView({ layout: t })}
                  title="${r.name} (${r.slots} slots)"
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
            .options=${_e(this._config.themes)}
            @selected=${(t) => {
      const r = K(
        t.detail,
        Object.keys(this._config.themes)
      );
      r && this._updateEditingView({ theme: r });
    }}
            @closed=${(t) => t.stopPropagation()}
          >
            ${Object.entries(this._config.themes).map(
      ([t, r]) => c`
                <mwc-list-item value=${t}>${r}</mwc-list-item>
              `
    )}
          </ha-select>
        </div>

        <!-- Widget slots -->
        <div class="section-title">Widgets</div>
        <div class="slots-grid">
          ${Array.from(
      { length: i },
      (t, r) => this._renderSlotEditor(r, i)
    )}
        </div>
      </div>
    `;
  }
  _renderSlotEditor(i, e) {
    var o;
    if (!this._config || !this._editingView) return p;
    const t = this._editingView.widgets.find((n) => n.slot === i), r = (t == null ? void 0 : t.type) || "", s = this._config.widget_types[r], a = this._editingView.layout;
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
              .value=${r}
              .options=${Ze(
      "-- Empty --",
      Object.fromEntries(
        Object.entries(this._config.widget_types).map(
          ([n, l]) => [n, l.name]
        )
      )
    )}
              @selected=${(n) => {
      const l = ["", ...Object.keys(this._config.widget_types)], h = K(n.detail, l) ?? "";
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

          ${s != null && s.needs_entity ? c`
                <div class="slot-field">
                  <ha-selector
                    .hass=${this.hass}
                    .selector=${{
      entity: s.entity_domains ? { domain: s.entity_domains } : {}
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

          ${(o = s == null ? void 0 : s.options) != null && o.length ? c`
                <div class="widget-options">
                  ${s.options.map(
      (n) => this._renderOptionField(i, t, n)
    )}
                </div>
              ` : p}
        </div>
      </ha-card>
    `;
  }
  _renderOptionField(i, e, t) {
    var s, a, o;
    const r = ((s = e == null ? void 0 : e.options) == null ? void 0 : s[t.key]) ?? t.default;
    switch (t.type) {
      case "boolean":
        return c`
          <div class="option-row">
            <label>${t.label}</label>
            <ha-switch
              .checked=${!!r}
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
              .value=${r || t.default || ""}
              .options=${t.options || []}
              @selected=${(n) => {
          const l = K(
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
              .selector=${Je(t)}
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
              .value=${r || ""}
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
              .value=${r || ""}
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
              .value=${r || ""}
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
              .value=${r}
              .label=${t.label}
              @value-changed=${(n) => this._updateWidgetOption(i, t.key, n.detail.value)}
            ></ha-selector>
            <div class="color-hex-input">
              <div
                class="color-preview-swatch"
                style="background-color: ${G(r)}"
              ></div>
              ${this._renderHexField(
          `${i}-${t.key}`,
          r,
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
              .value=${r || ""}
              .label=${t.label}
              @value-changed=${(n) => this._updateWidgetOption(i, t.key, n.detail.value)}
            ></ha-selector>
          </div>
        `;
      case "thresholds":
        return this._renderThresholdsEditor(i, t.key, r);
      case "progress_items":
        return this._renderProgressItemsEditor(i, t.key, r);
      case "status_entities":
        return this._renderStatusEntitiesEditor(i, t.key, r);
      case "timezone":
        return c`
          <div class="option-field">
            <ha-selector
              .hass=${this.hass}
              .selector=${Xe}
              .required=${!1}
              .label=${t.label}
              .value=${r || ""}
              @value-changed=${(n) => this._updateWidgetOption(i, t.key, n.detail.value)}
            ></ha-selector>
          </div>
        `;
      default:
        return p;
    }
  }
  _updateWidgetOption(i, e, t) {
    if (!this._editingView) return;
    const r = [...this._editingView.widgets], s = r.findIndex((a) => a.slot === i);
    if (s >= 0) {
      const a = r[s];
      r[s] = {
        ...a,
        options: { ...a.options || {}, [e]: t }
      };
    } else
      r.push({
        slot: i,
        type: "",
        options: { [e]: t }
      });
    this._editingView = { ...this._editingView, widgets: [...r] }, this.requestUpdate(), this._refreshPreview();
  }
  _renderThresholdsEditor(i, e, t) {
    const r = t || [];
    return c`
      <div class="option-field">
        <div class="array-editor">
          <div class="array-editor-header">
            <span>Color Thresholds</span>
          </div>
          <div class="array-items">
            ${r.map(
      (s, a) => c`
                <div class="threshold-item-container">
                  <div class="threshold-item">
                    <ha-selector
                      class="threshold-value"
                      .hass=${this.hass}
                      .selector=${de}
                      .required=${!1}
                      .label=${"Value"}
                      .value=${s.value}
                      @value-changed=${(o) => {
        const n = [...r];
        n[a] = { ...s, value: o.detail.value }, this._updateWidgetOption(i, e, n);
      }}
                    ></ha-selector>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ color_rgb: {} }}
                      .value=${s.color}
                      @value-changed=${(o) => {
        const n = [...r];
        n[a] = { ...s, color: o.detail.value }, this._updateWidgetOption(i, e, n);
      }}
                    ></ha-selector>
                    <ha-icon-button
                      .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                      @click=${() => {
        const o = r.filter((n, l) => l !== a);
        this._updateWidgetOption(i, e, o);
      }}
                    ></ha-icon-button>
                  </div>
                  <div class="threshold-hex-row">
                    <div
                      class="color-preview-swatch"
                      style="background-color: ${G(s.color)}"
                    ></div>
                    ${this._renderHexField(
        `${i}-${e}-${a}`,
        s.color,
        "#FF5500",
        (o) => {
          const n = [...r];
          n[a] = { ...s, color: o }, this._updateWidgetOption(i, e, n);
        }
      )}
                  </div>
                </div>
              `
    )}
            <div
              class="add-item-button"
              @click=${() => {
      const s = [...r, { value: 0, color: [255, 255, 0] }];
      this._updateWidgetOption(i, e, s);
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
    const r = t || [];
    return c`
      <div class="option-field">
        <div class="array-editor">
          <div class="array-editor-header">
            <span>Progress Items (${r.length})</span>
          </div>
          <div class="array-items">
            ${r.map((s, a) => {
      const o = `${i}-progress-${a}`, n = this._expandedItems.has(o);
      return c`
                <div class="array-item">
                  <div
                    class="array-item-header"
                    @click=${() => this._toggleItemExpanded(o)}
                  >
                    <span class="array-item-title">
                      ${s.label || s.entity_id || `Item ${a + 1}`}
                    </span>
                    <div class="array-item-actions">
                      <ha-icon-button
                        .path=${a > 0 ? "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z" : ""}
                        @click=${(l) => {
        l.stopPropagation(), a > 0 && this._moveArrayItem(i, e, r, a, -1);
      }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${a < r.length - 1 ? "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z" : ""}
                        @click=${(l) => {
        l.stopPropagation(), a < r.length - 1 && this._moveArrayItem(i, e, r, a, 1);
      }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                        @click=${(l) => {
        l.stopPropagation();
        const h = r.filter((v, d) => d !== a);
        this._updateWidgetOption(i, e, h);
      }}
                      ></ha-icon-button>
                    </div>
                  </div>
                  <div class="array-item-content ${n ? "" : "collapsed"}">
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ entity: {} }}
                      .value=${s.entity_id || ""}
                      .label=${"Entity"}
                      @value-changed=${(l) => this._updateArrayItem(i, e, r, a, {
        entity_id: l.detail.value
      })}
                    ></ha-selector>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${b}
                      .required=${!1}
                      .label=${"Label"}
                      .value=${s.label || ""}
                      @value-changed=${(l) => this._updateArrayItem(i, e, r, a, {
        label: l.detail.value
      })}
                    ></ha-selector>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${de}
                      .required=${!1}
                      .label=${"Target"}
                      .placeholder=${"100"}
                      .value=${s.target}
                      @value-changed=${(l) => this._updateArrayItem(i, e, r, a, {
        target: l.detail.value
      })}
                    ></ha-selector>
                    <ha-icon-picker
                      .hass=${this.hass}
                      label="Icon"
                      .value=${s.icon || ""}
                      @value-changed=${(l) => this._updateArrayItem(i, e, r, a, {
        icon: l.detail.value
      })}
                    ></ha-icon-picker>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ color_rgb: {} }}
                      .value=${s.color}
                      .label=${"Color"}
                      @value-changed=${(l) => this._updateArrayItem(i, e, r, a, {
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
      const s = [...r, { entity_id: "", target: 100 }];
      this._updateWidgetOption(i, e, s), this._expandedItems.add(`${i}-progress-${s.length - 1}`), this.requestUpdate();
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
    const r = t || [];
    return c`
      <div class="option-field">
        <div class="array-editor">
          <div class="array-editor-header">
            <span>Status Entities (${r.length})</span>
          </div>
          <div class="array-items">
            ${r.map((s, a) => {
      const o = `${i}-status-${a}`, n = this._expandedItems.has(o);
      return c`
                <div class="array-item">
                  <div
                    class="array-item-header"
                    @click=${() => this._toggleItemExpanded(o)}
                  >
                    <span class="array-item-title">
                      ${s.label || s.entity_id || `Entity ${a + 1}`}
                    </span>
                    <div class="array-item-actions">
                      <ha-icon-button
                        .path=${a > 0 ? "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z" : ""}
                        @click=${(l) => {
        l.stopPropagation(), a > 0 && this._moveArrayItem(i, e, r, a, -1);
      }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${a < r.length - 1 ? "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z" : ""}
                        @click=${(l) => {
        l.stopPropagation(), a < r.length - 1 && this._moveArrayItem(i, e, r, a, 1);
      }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                        @click=${(l) => {
        l.stopPropagation();
        const h = r.filter((v, d) => d !== a);
        this._updateWidgetOption(i, e, h);
      }}
                      ></ha-icon-button>
                    </div>
                  </div>
                  <div class="array-item-content ${n ? "" : "collapsed"}">
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ entity: {} }}
                      .value=${s.entity_id || ""}
                      .label=${"Entity"}
                      @value-changed=${(l) => this._updateArrayItem(i, e, r, a, {
        entity_id: l.detail.value
      })}
                    ></ha-selector>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${b}
                      .required=${!1}
                      .label=${"Label"}
                      .value=${s.label || ""}
                      @value-changed=${(l) => this._updateArrayItem(i, e, r, a, {
        label: l.detail.value
      })}
                    ></ha-selector>
                    <ha-icon-picker
                      .hass=${this.hass}
                      label="Icon"
                      .value=${s.icon || ""}
                      @value-changed=${(l) => this._updateArrayItem(i, e, r, a, {
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
      const s = [...r, { entity_id: "" }];
      this._updateWidgetOption(i, e, s), this._expandedItems.add(`${i}-status-${s.length - 1}`), this.requestUpdate();
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
  _renderHexField(i, e, t, r) {
    const s = () => {
      const a = this._hexDrafts.get(i);
      this._hexDrafts.delete(i);
      const o = a === void 0 ? null : Re(a);
      o && r(o);
    };
    return c`
      <ha-selector
        class="hex-input"
        .hass=${this.hass}
        .selector=${b}
        .required=${!1}
        .label=${"Hex (fallback)"}
        .placeholder=${t}
        .value=${G(e)}
        @value-changed=${(a) => this._hexDrafts.set(i, a.detail.value ?? "")}
        @focusout=${s}
        @keydown=${(a) => {
      a.key === "Enter" && s();
    }}
      ></ha-selector>
    `;
  }
  _toggleItemExpanded(i) {
    this._expandedItems.has(i) ? this._expandedItems.delete(i) : this._expandedItems.add(i), this._expandedItems = new Set(this._expandedItems);
  }
  _updateArrayItem(i, e, t, r, s) {
    const a = [...t];
    a[r] = { ...a[r], ...s }, this._updateWidgetOption(i, e, a);
  }
  _moveArrayItem(i, e, t, r, s) {
    const a = r + s;
    if (a < 0 || a >= t.length) return;
    const o = [...t];
    [o[r], o[a]] = [o[a], o[r]], this._updateWidgetOption(i, e, o);
  }
  _renderPositionGrid(i, e, t) {
    let r = 2, s = !1;
    switch (t) {
      case "fullscreen":
        r = 1;
        break;
      case "grid_2x2":
        r = 2;
        break;
      case "grid_2x3":
        r = 3;
        break;
      case "grid_3x2":
        r = 2;
        break;
      case "hero":
        r = 3, s = !0;
        break;
      case "split":
        r = 2;
        break;
      case "three_column":
        r = 3;
        break;
      default:
        r = 2;
    }
    const a = [];
    if (s) {
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
      <div class="position-grid cols-${r}">${a}</div>
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
    }[i] || { cls: "", cells: 4 }, r = Array.from({ length: t.cells }, () => c`<div></div>`);
    return c`<div class="layout-icon ${t.cls}">${r}</div>`;
  }
  _swapSlots(i, e) {
    i === e || !this._editingView || (this._editingView = {
      ...this._editingView,
      widgets: qe(this._editingView.widgets, i, e)
    }, this._refreshPreview());
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

    .action-error {
      display: block;
      margin-bottom: 16px;
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

    .preview-error {
      box-sizing: border-box;
      padding: 16px;
      text-align: center;
      overflow-wrap: anywhere;
      color: var(--error-color);
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
  N({ attribute: !1 })
], u.prototype, "hass", 2);
g([
  N({ type: Boolean })
], u.prototype, "narrow", 2);
g([
  N({ attribute: !1 })
], u.prototype, "route", 2);
g([
  N({ attribute: !1 })
], u.prototype, "panel", 2);
g([
  f()
], u.prototype, "_page", 2);
g([
  f()
], u.prototype, "_config", 2);
g([
  f()
], u.prototype, "_views", 2);
g([
  f()
], u.prototype, "_devices", 2);
g([
  f()
], u.prototype, "_editingView", 2);
g([
  f()
], u.prototype, "_previewImage", 2);
g([
  f()
], u.prototype, "_previewLoading", 2);
g([
  f()
], u.prototype, "_previewError", 2);
g([
  f()
], u.prototype, "_loading", 2);
g([
  f()
], u.prototype, "_loadError", 2);
g([
  f()
], u.prototype, "_actionError", 2);
g([
  f()
], u.prototype, "_saving", 2);
g([
  f()
], u.prototype, "_expandedItems", 2);
g([
  f()
], u.prototype, "_viewPreviews", 2);
g([
  f()
], u.prototype, "_createViewDialogOpen", 2);
g([
  f()
], u.prototype, "_newViewName", 2);
g([
  f()
], u.prototype, "_creatingView", 2);
g([
  f()
], u.prototype, "_createViewError", 2);
u = g([
  Ue("geekmagic-panel")
], u);
export {
  u as GeekMagicPanel
};
