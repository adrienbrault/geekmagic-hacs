/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const D = globalThis, K = D.ShadowRoot && (D.ShadyCSS === void 0 || D.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, G = Symbol(), Q = /* @__PURE__ */ new WeakMap();
let pe = class {
  constructor(e, t, s) {
    if (this._$cssResult$ = !0, s !== G) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
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
const fe = (o) => new pe(typeof o == "string" ? o : o + "", void 0, G), ye = (o, ...e) => {
  const t = o.length === 1 ? o[0] : e.reduce((s, i, r) => s + ((a) => {
    if (a._$cssResult$ === !0) return a.cssText;
    if (typeof a == "number") return a;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + a + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(i) + o[r + 1], o[0]);
  return new pe(t, o, G);
}, we = (o, e) => {
  if (K) o.adoptedStyleSheets = e.map((t) => t instanceof CSSStyleSheet ? t : t.styleSheet);
  else for (const t of e) {
    const s = document.createElement("style"), i = D.litNonce;
    i !== void 0 && s.setAttribute("nonce", i), s.textContent = t.cssText, o.appendChild(s);
  }
}, ee = K ? (o) => o : (o) => o instanceof CSSStyleSheet ? ((e) => {
  let t = "";
  for (const s of e.cssRules) t += s.cssText;
  return fe(t);
})(o) : o;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: $e, defineProperty: be, getOwnPropertyDescriptor: xe, getOwnPropertyNames: Ve, getOwnPropertySymbols: Ae, getPrototypeOf: ke } = Object, w = globalThis, te = w.trustedTypes, Ee = te ? te.emptyScript : "", F = w.reactiveElementPolyfillSupport, C = (o, e) => o, j = { toAttribute(o, e) {
  switch (e) {
    case Boolean:
      o = o ? Ee : null;
      break;
    case Object:
    case Array:
      o = o == null ? o : JSON.stringify(o);
  }
  return o;
}, fromAttribute(o, e) {
  let t = o;
  switch (e) {
    case Boolean:
      t = o !== null;
      break;
    case Number:
      t = o === null ? null : Number(o);
      break;
    case Object:
    case Array:
      try {
        t = JSON.parse(o);
      } catch {
        t = null;
      }
  }
  return t;
} }, J = (o, e) => !$e(o, e), ie = { attribute: !0, type: String, converter: j, reflect: !1, useDefault: !1, hasChanged: J };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), w.litPropertyMetadata ?? (w.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let A = class extends HTMLElement {
  static addInitializer(e) {
    this._$Ei(), (this.l ?? (this.l = [])).push(e);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(e, t = ie) {
    if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
      const s = Symbol(), i = this.getPropertyDescriptor(e, s, t);
      i !== void 0 && be(this.prototype, e, i);
    }
  }
  static getPropertyDescriptor(e, t, s) {
    const { get: i, set: r } = xe(this.prototype, e) ?? { get() {
      return this[t];
    }, set(a) {
      this[t] = a;
    } };
    return { get: i, set(a) {
      const n = i == null ? void 0 : i.call(this);
      r == null || r.call(this, a), this.requestUpdate(e, n, s);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(e) {
    return this.elementProperties.get(e) ?? ie;
  }
  static _$Ei() {
    if (this.hasOwnProperty(C("elementProperties"))) return;
    const e = ke(this);
    e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(C("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(C("properties"))) {
      const t = this.properties, s = [...Ve(t), ...Ae(t)];
      for (const i of s) this.createProperty(i, t[i]);
    }
    const e = this[Symbol.metadata];
    if (e !== null) {
      const t = litPropertyMetadata.get(e);
      if (t !== void 0) for (const [s, i] of t) this.elementProperties.set(s, i);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t, s] of this.elementProperties) {
      const i = this._$Eu(t, s);
      i !== void 0 && this._$Eh.set(i, t);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(e) {
    const t = [];
    if (Array.isArray(e)) {
      const s = new Set(e.flat(1 / 0).reverse());
      for (const i of s) t.unshift(ee(i));
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
    var r;
    const s = this.constructor.elementProperties.get(e), i = this.constructor._$Eu(e, s);
    if (i !== void 0 && s.reflect === !0) {
      const a = (((r = s.converter) == null ? void 0 : r.toAttribute) !== void 0 ? s.converter : j).toAttribute(t, s.type);
      this._$Em = e, a == null ? this.removeAttribute(i) : this.setAttribute(i, a), this._$Em = null;
    }
  }
  _$AK(e, t) {
    var r, a;
    const s = this.constructor, i = s._$Eh.get(e);
    if (i !== void 0 && this._$Em !== i) {
      const n = s.getPropertyOptions(i), l = typeof n.converter == "function" ? { fromAttribute: n.converter } : ((r = n.converter) == null ? void 0 : r.fromAttribute) !== void 0 ? n.converter : j;
      this._$Em = i;
      const d = l.fromAttribute(t, n.type);
      this[i] = d ?? ((a = this._$Ej) == null ? void 0 : a.get(i)) ?? d, this._$Em = null;
    }
  }
  requestUpdate(e, t, s) {
    var i;
    if (e !== void 0) {
      const r = this.constructor, a = this[e];
      if (s ?? (s = r.getPropertyOptions(e)), !((s.hasChanged ?? J)(a, t) || s.useDefault && s.reflect && a === ((i = this._$Ej) == null ? void 0 : i.get(e)) && !this.hasAttribute(r._$Eu(e, s)))) return;
      this.C(e, t, s);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(e, t, { useDefault: s, reflect: i, wrapped: r }, a) {
    s && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(e) && (this._$Ej.set(e, a ?? t ?? this[e]), r !== !0 || a !== void 0) || (this._$AL.has(e) || (this.hasUpdated || s || (t = void 0), this._$AL.set(e, t)), i === !0 && this._$Em !== e && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(e));
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
        for (const [r, a] of this._$Ep) this[r] = a;
        this._$Ep = void 0;
      }
      const i = this.constructor.elementProperties;
      if (i.size > 0) for (const [r, a] of i) {
        const { wrapped: n } = a, l = this[r];
        n !== !0 || this._$AL.has(r) || l === void 0 || this.C(r, void 0, a, l);
      }
    }
    let e = !1;
    const t = this._$AL;
    try {
      e = this.shouldUpdate(t), e ? (this.willUpdate(t), (s = this._$EO) == null || s.forEach((i) => {
        var r;
        return (r = i.hostUpdate) == null ? void 0 : r.call(i);
      }), this.update(t)) : this._$EM();
    } catch (i) {
      throw e = !1, this._$EM(), i;
    }
    e && this._$AE(t);
  }
  willUpdate(e) {
  }
  _$AE(e) {
    var t;
    (t = this._$EO) == null || t.forEach((s) => {
      var i;
      return (i = s.hostUpdated) == null ? void 0 : i.call(s);
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
A.elementStyles = [], A.shadowRootOptions = { mode: "open" }, A[C("elementProperties")] = /* @__PURE__ */ new Map(), A[C("finalized")] = /* @__PURE__ */ new Map(), F == null || F({ ReactiveElement: A }), (w.reactiveElementVersions ?? (w.reactiveElementVersions = [])).push("2.1.1");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const H = globalThis, z = H.trustedTypes, se = z ? z.createPolicy("lit-html", { createHTML: (o) => o }) : void 0, ue = "$lit$", y = `lit$${Math.random().toFixed(9).slice(2)}$`, ge = "?" + y, Se = `<${ge}>`, V = document, I = () => V.createComment(""), L = (o) => o === null || typeof o != "object" && typeof o != "function", Y = Array.isArray, Pe = (o) => Y(o) || typeof (o == null ? void 0 : o[Symbol.iterator]) == "function", B = `[ 	
\f\r]`, S = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, re = /-->/g, ae = />/g, $ = RegExp(`>|${B}(?:([^\\s"'>=/]+)(${B}*=${B}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), oe = /'/g, ne = /"/g, ve = /^(?:script|style|textarea|title)$/i, Ce = (o) => (e, ...t) => ({ _$litType$: o, strings: e, values: t }), h = Ce(1), k = Symbol.for("lit-noChange"), p = Symbol.for("lit-nothing"), le = /* @__PURE__ */ new WeakMap(), b = V.createTreeWalker(V, 129);
function me(o, e) {
  if (!Y(o) || !o.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return se !== void 0 ? se.createHTML(e) : e;
}
const He = (o, e) => {
  const t = o.length - 1, s = [];
  let i, r = e === 2 ? "<svg>" : e === 3 ? "<math>" : "", a = S;
  for (let n = 0; n < t; n++) {
    const l = o[n];
    let d, g, c = -1, u = 0;
    for (; u < l.length && (a.lastIndex = u, g = a.exec(l), g !== null); ) u = a.lastIndex, a === S ? g[1] === "!--" ? a = re : g[1] !== void 0 ? a = ae : g[2] !== void 0 ? (ve.test(g[2]) && (i = RegExp("</" + g[2], "g")), a = $) : g[3] !== void 0 && (a = $) : a === $ ? g[0] === ">" ? (a = i ?? S, c = -1) : g[1] === void 0 ? c = -2 : (c = a.lastIndex - g[2].length, d = g[1], a = g[3] === void 0 ? $ : g[3] === '"' ? ne : oe) : a === ne || a === oe ? a = $ : a === re || a === ae ? a = S : (a = $, i = void 0);
    const f = a === $ && o[n + 1].startsWith("/>") ? " " : "";
    r += a === S ? l + Se : c >= 0 ? (s.push(d), l.slice(0, c) + ue + l.slice(c) + y + f) : l + y + (c === -2 ? n : f);
  }
  return [me(o, r + (o[t] || "<?>") + (e === 2 ? "</svg>" : e === 3 ? "</math>" : "")), s];
};
class O {
  constructor({ strings: e, _$litType$: t }, s) {
    let i;
    this.parts = [];
    let r = 0, a = 0;
    const n = e.length - 1, l = this.parts, [d, g] = He(e, t);
    if (this.el = O.createElement(d, s), b.currentNode = this.el.content, t === 2 || t === 3) {
      const c = this.el.content.firstChild;
      c.replaceWith(...c.childNodes);
    }
    for (; (i = b.nextNode()) !== null && l.length < n; ) {
      if (i.nodeType === 1) {
        if (i.hasAttributes()) for (const c of i.getAttributeNames()) if (c.endsWith(ue)) {
          const u = g[a++], f = i.getAttribute(c).split(y), W = /([.?@])?(.*)/.exec(u);
          l.push({ type: 1, index: r, name: W[2], strings: f, ctor: W[1] === "." ? Ie : W[1] === "?" ? Le : W[1] === "@" ? Oe : R }), i.removeAttribute(c);
        } else c.startsWith(y) && (l.push({ type: 6, index: r }), i.removeAttribute(c));
        if (ve.test(i.tagName)) {
          const c = i.textContent.split(y), u = c.length - 1;
          if (u > 0) {
            i.textContent = z ? z.emptyScript : "";
            for (let f = 0; f < u; f++) i.append(c[f], I()), b.nextNode(), l.push({ type: 2, index: ++r });
            i.append(c[u], I());
          }
        }
      } else if (i.nodeType === 8) if (i.data === ge) l.push({ type: 2, index: r });
      else {
        let c = -1;
        for (; (c = i.data.indexOf(y, c + 1)) !== -1; ) l.push({ type: 7, index: r }), c += y.length - 1;
      }
      r++;
    }
  }
  static createElement(e, t) {
    const s = V.createElement("template");
    return s.innerHTML = e, s;
  }
}
function E(o, e, t = o, s) {
  var a, n;
  if (e === k) return e;
  let i = s !== void 0 ? (a = t._$Co) == null ? void 0 : a[s] : t._$Cl;
  const r = L(e) ? void 0 : e._$litDirective$;
  return (i == null ? void 0 : i.constructor) !== r && ((n = i == null ? void 0 : i._$AO) == null || n.call(i, !1), r === void 0 ? i = void 0 : (i = new r(o), i._$AT(o, t, s)), s !== void 0 ? (t._$Co ?? (t._$Co = []))[s] = i : t._$Cl = i), i !== void 0 && (e = E(o, i._$AS(o, e.values), i, s)), e;
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
    const { el: { content: t }, parts: s } = this._$AD, i = ((e == null ? void 0 : e.creationScope) ?? V).importNode(t, !0);
    b.currentNode = i;
    let r = b.nextNode(), a = 0, n = 0, l = s[0];
    for (; l !== void 0; ) {
      if (a === l.index) {
        let d;
        l.type === 2 ? d = new T(r, r.nextSibling, this, e) : l.type === 1 ? d = new l.ctor(r, l.name, l.strings, this, e) : l.type === 6 && (d = new Te(r, this, e)), this._$AV.push(d), l = s[++n];
      }
      a !== (l == null ? void 0 : l.index) && (r = b.nextNode(), a++);
    }
    return b.currentNode = V, i;
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
  constructor(e, t, s, i) {
    this.type = 2, this._$AH = p, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = s, this.options = i, this._$Cv = (i == null ? void 0 : i.isConnected) ?? !0;
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
    e = E(this, e, t), L(e) ? e === p || e == null || e === "" ? (this._$AH !== p && this._$AR(), this._$AH = p) : e !== this._$AH && e !== k && this._(e) : e._$litType$ !== void 0 ? this.$(e) : e.nodeType !== void 0 ? this.T(e) : Pe(e) ? this.k(e) : this._(e);
  }
  O(e) {
    return this._$AA.parentNode.insertBefore(e, this._$AB);
  }
  T(e) {
    this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
  }
  _(e) {
    this._$AH !== p && L(this._$AH) ? this._$AA.nextSibling.data = e : this.T(V.createTextNode(e)), this._$AH = e;
  }
  $(e) {
    var r;
    const { values: t, _$litType$: s } = e, i = typeof s == "number" ? this._$AC(e) : (s.el === void 0 && (s.el = O.createElement(me(s.h, s.h[0]), this.options)), s);
    if (((r = this._$AH) == null ? void 0 : r._$AD) === i) this._$AH.p(t);
    else {
      const a = new Me(i, this), n = a.u(this.options);
      a.p(t), this.T(n), this._$AH = a;
    }
  }
  _$AC(e) {
    let t = le.get(e.strings);
    return t === void 0 && le.set(e.strings, t = new O(e)), t;
  }
  k(e) {
    Y(this._$AH) || (this._$AH = [], this._$AR());
    const t = this._$AH;
    let s, i = 0;
    for (const r of e) i === t.length ? t.push(s = new T(this.O(I()), this.O(I()), this, this.options)) : s = t[i], s._$AI(r), i++;
    i < t.length && (this._$AR(s && s._$AB.nextSibling, i), t.length = i);
  }
  _$AR(e = this._$AA.nextSibling, t) {
    var s;
    for ((s = this._$AP) == null ? void 0 : s.call(this, !1, !0, t); e !== this._$AB; ) {
      const i = e.nextSibling;
      e.remove(), e = i;
    }
  }
  setConnected(e) {
    var t;
    this._$AM === void 0 && (this._$Cv = e, (t = this._$AP) == null || t.call(this, e));
  }
}
class R {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(e, t, s, i, r) {
    this.type = 1, this._$AH = p, this._$AN = void 0, this.element = e, this.name = t, this._$AM = i, this.options = r, s.length > 2 || s[0] !== "" || s[1] !== "" ? (this._$AH = Array(s.length - 1).fill(new String()), this.strings = s) : this._$AH = p;
  }
  _$AI(e, t = this, s, i) {
    const r = this.strings;
    let a = !1;
    if (r === void 0) e = E(this, e, t, 0), a = !L(e) || e !== this._$AH && e !== k, a && (this._$AH = e);
    else {
      const n = e;
      let l, d;
      for (e = r[0], l = 0; l < r.length - 1; l++) d = E(this, n[s + l], t, l), d === k && (d = this._$AH[l]), a || (a = !L(d) || d !== this._$AH[l]), d === p ? e = p : e !== p && (e += (d ?? "") + r[l + 1]), this._$AH[l] = d;
    }
    a && !i && this.j(e);
  }
  j(e) {
    e === p ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
  }
}
class Ie extends R {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(e) {
    this.element[this.name] = e === p ? void 0 : e;
  }
}
class Le extends R {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(e) {
    this.element.toggleAttribute(this.name, !!e && e !== p);
  }
}
class Oe extends R {
  constructor(e, t, s, i, r) {
    super(e, t, s, i, r), this.type = 5;
  }
  _$AI(e, t = this) {
    if ((e = E(this, e, t, 0) ?? p) === k) return;
    const s = this._$AH, i = e === p && s !== p || e.capture !== s.capture || e.once !== s.once || e.passive !== s.passive, r = e !== p && (s === p || i);
    i && this.element.removeEventListener(this.name, this, s), r && this.element.addEventListener(this.name, this, e), this._$AH = e;
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
    E(this, e);
  }
}
const q = H.litHtmlPolyfillSupport;
q == null || q(O, T), (H.litHtmlVersions ?? (H.litHtmlVersions = [])).push("3.3.1");
const Ue = (o, e, t) => {
  const s = (t == null ? void 0 : t.renderBefore) ?? e;
  let i = s._$litPart$;
  if (i === void 0) {
    const r = (t == null ? void 0 : t.renderBefore) ?? null;
    s._$litPart$ = i = new T(e.insertBefore(I(), r), r, void 0, t ?? {});
  }
  return i._$AI(o), i;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const x = globalThis;
class M extends A {
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
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Ue(t, this.renderRoot, this.renderOptions);
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
M._$litElement$ = !0, M.finalized = !0, (he = x.litElementHydrateSupport) == null || he.call(x, { LitElement: M });
const Z = x.litElementPolyfillSupport;
Z == null || Z({ LitElement: M });
(x.litElementVersions ?? (x.litElementVersions = [])).push("4.2.1");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const We = { attribute: !0, type: String, converter: j, reflect: !1, hasChanged: J }, Ne = (o = We, e, t) => {
  const { kind: s, metadata: i } = t;
  let r = globalThis.litPropertyMetadata.get(i);
  if (r === void 0 && globalThis.litPropertyMetadata.set(i, r = /* @__PURE__ */ new Map()), s === "setter" && ((o = Object.create(o)).wrapped = !0), r.set(t.name, o), s === "accessor") {
    const { name: a } = t;
    return { set(n) {
      const l = e.get.call(this);
      e.set.call(this, n), this.requestUpdate(a, l, o);
    }, init(n) {
      return n !== void 0 && this.C(a, void 0, o, n), n;
    } };
  }
  if (s === "setter") {
    const { name: a } = t;
    return function(n) {
      const l = this[a];
      e.call(this, n), this.requestUpdate(a, l, o);
    };
  }
  throw Error("Unsupported decorator location: " + s);
};
function U(o) {
  return (e, t) => typeof t == "object" ? Ne(o, e, t) : ((s, i, r) => {
    const a = i.hasOwnProperty(r);
    return i.constructor.createProperty(r, s), a ? Object.getOwnPropertyDescriptor(i, r) : void 0;
  })(o, e, t);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function _(o) {
  return U({ ...o, state: !0, attribute: !1 });
}
function N(o) {
  if (!o || o.length !== 3) return "#000000";
  const [e, t, s] = o;
  return `#${[e, t, s].map((i) => Math.max(0, Math.min(255, i)).toString(16).padStart(2, "0")).join("")}`;
}
function ce(o) {
  const e = o.trim();
  if (!e) return null;
  const t = e.match(/^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/);
  if (t) {
    let r = t[1];
    return r.length === 3 && (r = r[0] + r[0] + r[1] + r[1] + r[2] + r[2]), [
      parseInt(r.slice(0, 2), 16),
      parseInt(r.slice(2, 4), 16),
      parseInt(r.slice(4, 6), 16)
    ];
  }
  const s = e.match(/^(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})$/);
  if (s) {
    const r = Math.min(255, parseInt(s[1], 10)), a = Math.min(255, parseInt(s[2], 10)), n = Math.min(255, parseInt(s[3], 10));
    return [r, a, n];
  }
  const i = e.match(
    /^rgb\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/i
  );
  if (i) {
    const r = Math.min(255, parseInt(i[1], 10)), a = Math.min(255, parseInt(i[2], 10)), n = Math.min(255, parseInt(i[3], 10));
    return [r, a, n];
  }
  return null;
}
function P(o, e) {
  if (o.value !== void 0 && o.value !== null)
    return o.value;
  if (o.index !== void 0 && o.index !== null)
    return e[o.index];
}
function _e(o) {
  return Object.entries(o).map(([e, t]) => ({ value: e, label: t }));
}
function de(o, e) {
  return [{ value: "", label: o }, ..._e(e)];
}
var De = Object.defineProperty, m = (o, e, t, s) => {
  for (var i = void 0, r = o.length - 1, a; r >= 0; r--)
    (a = o[r]) && (i = a(e, t, i) || i);
  return i && De(e, t, i), i;
};
const je = (() => {
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
})();
function ze(o, e) {
  let t;
  return (...s) => {
    clearTimeout(t), t = setTimeout(() => o(...s), e);
  };
}
const X = class X extends M {
  constructor() {
    super(...arguments), this.narrow = !1, this._page = "main", this._config = null, this._views = [], this._devices = [], this._editingView = null, this._previewImage = null, this._previewLoading = !1, this._loading = !0, this._saving = !1, this._expandedItems = /* @__PURE__ */ new Set(), this._viewPreviews = /* @__PURE__ */ new Map(), this._createViewDialogOpen = !1, this._newViewName = "", this._creatingView = !1, this._createViewError = null, this._refreshPreview = ze(async () => {
      if (this._editingView) {
        this._previewLoading = !0;
        try {
          const e = await this.hass.connection.sendMessagePromise({
            type: "geekmagic/preview/render",
            view_config: {
              layout: this._editingView.layout,
              theme: this._editingView.theme,
              widgets: this._editingView.widgets,
              background_image: this._editingView.background_image || "",
              background_mode: this._editingView.background_mode || "stretch",
              background_entity: this._editingView.background_entity || "",
              widget_contrast: this._editingView.widget_contrast ?? 0,
              text_opacity: this._editingView.text_opacity ?? 1
            }
          });
          this._previewImage = e.image;
        } catch (e) {
          console.error("Failed to render preview:", e);
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
      const [e, t, s] = await Promise.all([
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
      this._config = e, this._views = t.views, this._devices = s.devices, this._loadViewPreviews();
    } catch (e) {
      console.error("Failed to load GeekMagic config:", e);
    } finally {
      this._loading = !1;
    }
  }
  async _loadViewPreviews() {
    const e = this._views.map(async (i) => {
      try {
        const r = await this.hass.connection.sendMessagePromise({
          type: "geekmagic/preview/render",
          view_config: {
            layout: i.layout,
            theme: i.theme,
            widgets: i.widgets,
            background_image: i.background_image || "",
            background_mode: i.background_mode || "stretch",
            background_entity: i.background_entity || "",
            widget_contrast: i.widget_contrast ?? 0,
            text_opacity: i.text_opacity ?? 1
          }
        });
        return { id: i.id, image: r.image };
      } catch (r) {
        return console.error(`Failed to load preview for view ${i.id}:`, r), { id: i.id, image: null };
      }
    }), t = await Promise.all(e), s = /* @__PURE__ */ new Map();
    for (const i of t)
      i.image && s.set(i.id, i.image);
    this._viewPreviews = s;
  }
  _suggestViewName() {
    const e = new Set(this._views.map((i) => i.name)), t = "New View";
    if (!e.has(t)) return t;
    let s = 2;
    for (; e.has(`${t} ${s}`); )
      s += 1;
    return `${t} ${s}`;
  }
  async _openCreateViewDialog() {
    var e;
    this._newViewName = this._suggestViewName(), this._createViewError = null, this._createViewDialogOpen = !0, await this.updateComplete, (e = this.renderRoot.querySelector(".create-view-name")) == null || e.focus();
  }
  _closeCreateViewDialog() {
    this._creatingView || (this._createViewDialogOpen = !1, this._createViewError = null);
  }
  _handleCreateViewDialogKeydown(e) {
    if (e.key === "Escape") {
      e.stopPropagation(), this._closeCreateViewDialog();
      return;
    }
    e.key === "Enter" && !e.shiftKey && (e.preventDefault(), this._createView());
  }
  async _createView() {
    const e = this._newViewName.trim();
    if (!(!e || this._creatingView)) {
      this._creatingView = !0, this._createViewError = null;
      try {
        const t = await this.hass.connection.sendMessagePromise({
          type: "geekmagic/views/create",
          name: e,
          layout: "grid_2x2",
          theme: "watchos",
          widgets: [],
          background_image: "",
          background_mode: "stretch",
          background_entity: "",
          widget_contrast: 0.5,
          text_opacity: 1
        });
        this._views = [...this._views, t.view], this._createViewDialogOpen = !1, this._newViewName = "", this._editView(t.view);
      } catch (t) {
        console.error("Failed to create view:", t), this._createViewError = "Could not create view. Check Home Assistant logs and try again.";
      } finally {
        this._creatingView = !1;
      }
    }
  }
  _editView(e) {
    this._editingView = { ...e, widgets: [...e.widgets] }, this._page = "editor", this._refreshPreview();
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
          widgets: this._editingView.widgets,
          background_image: this._editingView.background_image || "",
          background_mode: this._editingView.background_mode || "stretch",
          background_entity: this._editingView.background_entity || "",
          widget_contrast: this._editingView.widget_contrast ?? 0,
          text_opacity: this._editingView.text_opacity ?? 1
        }), this._views = this._views.map(
          (e) => e.id === this._editingView.id ? this._editingView : e
        ), this._page = "main", this._editingView = null, this._loadViewPreviews();
      } catch (e) {
        console.error("Failed to save view:", e);
      } finally {
        this._saving = !1;
      }
    }
  }
  async _deleteView(e) {
    if (confirm(`Delete view "${e.name}"?`))
      try {
        await this.hass.connection.sendMessagePromise({
          type: "geekmagic/views/delete",
          view_id: e.id
        }), this._views = this._views.filter((t) => t.id !== e.id);
      } catch (t) {
        console.error("Failed to delete view:", t);
      }
  }
  _updateEditingView(e) {
    if (this._editingView) {
      if (e.layout !== void 0 && e.layout !== this._editingView.layout) {
        const t = e.layout === "custom", s = this._editingView.widgets.map((i, r) => ({
          ...i,
          slot: t ? r : i.slot ?? r,
          x: i.x ?? 0,
          y: i.y ?? 0,
          width: i.width ?? 240,
          height: i.height ?? 240
        }));
        this._editingView = { ...this._editingView, ...e, widgets: s }, this._refreshPreview();
        return;
      }
      this._editingView = { ...this._editingView, ...e }, this._refreshPreview();
    }
  }
  _isCustomLayout() {
    var e;
    return ((e = this._editingView) == null ? void 0 : e.layout) === "custom";
  }
  _updateWidget(e, t) {
    if (!this._editingView) return;
    if (t.type === "clock") {
      const r = Intl.DateTimeFormat().resolvedOptions().timeZone;
      t = {
        ...t,
        options: { ...t.options, timezone: r }
      };
    }
    const s = [...this._editingView.widgets];
    if (this._isCustomLayout())
      if (e >= 0 && e < s.length)
        s[e] = { ...s[e], ...t };
      else {
        const r = s.length, a = r % 4, n = Math.floor(r / 4);
        s.push({
          x: 10 + a * 60,
          y: 10 + n * 60,
          width: 50,
          height: 50,
          slot: r,
          type: "",
          ...t
        });
      }
    else {
      const r = s.findIndex((a) => a.slot === e);
      r >= 0 ? s[r] = { ...s[r], ...t } : s.push({ slot: e, type: "", ...t });
    }
    this._editingView = { ...this._editingView, widgets: [...s] }, this.requestUpdate(), this._refreshPreview();
  }
  async _toggleDeviceView(e, t, s) {
    const i = s ? [...e.assigned_views, t] : e.assigned_views.filter((r) => r !== t);
    try {
      await this.hass.connection.sendMessagePromise({
        type: "geekmagic/devices/assign_views",
        entry_id: e.entry_id,
        view_ids: i
      }), this._devices = this._devices.map(
        (r) => r.entry_id === e.entry_id ? { ...r, assigned_views: i } : r
      );
    } catch (r) {
      console.error("Failed to update device views:", r);
    }
  }
  render() {
    return this._loading ? h`
        <div class="loading">
          <ha-circular-progress indeterminate></ha-circular-progress>
        </div>
      ` : h`
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
    return h`
      <!-- Devices Section -->
      <div class="section">
        <h2 class="section-header">Devices</h2>
        ${this._devices.length === 0 ? h`
              <div class="empty-state-inline">
                <ha-icon icon="mdi:monitor-off"></ha-icon>
                <span>No devices configured. Add a device through Settings → Devices & Services.</span>
              </div>
            ` : h`
              <div class="devices-list">
                ${this._devices.map(
      (e) => h`
                    <ha-card>
                      <div class="card-content" style="padding-top: 16px;">
                        <div class="device-header">
                          <span class="device-name">${e.name}</span>
                          <span class="device-status ${e.online ? "online" : "offline"}">
                            <a href="http://${e.host}" target="_blank" rel="noopener noreferrer">${e.online ? "Online" : "Offline"}</a>
                          </span>
                        </div>
                        <div class="views-checkboxes">
                          ${this._views.length === 0 ? h`<p style="color: var(--secondary-text-color); margin: 8px 0 0;">
                                No views available. Create a view below.
                              </p>` : this._views.map(
        (t) => h`
                                  <label class="view-checkbox">
                                    <ha-checkbox
                                      .checked=${e.assigned_views.includes(t.id)}
                                      @change=${(s) => this._toggleDeviceView(
          e,
          t.id,
          s.target.checked
        )}
                                    ></ha-checkbox>
                                    ${t.name}
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
      (e) => {
        var t, s, i;
        return h`
              <ha-card class="view-card" @click=${() => this._editView(e)}>
                <div class="view-card-content">
                  <div class="view-card-preview">
                    ${this._viewPreviews.has(e.id) ? h`<img
                          class="view-preview-image"
                          src="data:image/png;base64,${this._viewPreviews.get(e.id)}"
                          alt="${e.name}"
                        />` : h`<div class="view-preview-placeholder">
                          <ha-circular-progress indeterminate size="small"></ha-circular-progress>
                        </div>`}
                  </div>
                  <div class="view-card-info">
                    <div class="view-card-header">
                      <h3>${e.name}</h3>
                      <ha-icon-button
                        .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                        @click=${(r) => {
          r.stopPropagation(), this._deleteView(e);
        }}
                      ></ha-icon-button>
                    </div>
                    <div class="card-meta">
                      ${((s = (t = this._config) == null ? void 0 : t.layout_types[e.layout]) == null ? void 0 : s.name) || e.layout}
                      &bull; ${((i = this._config) == null ? void 0 : i.themes[e.theme]) || e.theme}
                      &bull; ${e.widgets.length} widgets
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
    const e = this._newViewName.trim();
    return h`
      <div
        class="dialog-backdrop"
        @click=${() => this._closeCreateViewDialog()}
        @keydown=${(t) => this._handleCreateViewDialogKeydown(t)}
      >
        <ha-card
          class="dialog-card"
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-view-title"
          @click=${(t) => t.stopPropagation()}
        >
          <div class="dialog-content">
            <h2 id="create-view-title">Create View</h2>
            <p>Name the dashboard view before opening the editor.</p>
            <ha-input
              class="create-view-name"
              label="View name"
              .value=${this._newViewName}
              @input=${(t) => {
      this._newViewName = t.target.value;
    }}
              @keydown=${(t) => this._handleCreateViewDialogKeydown(t)}
            ></ha-input>
            ${this._createViewError ? h`<div class="dialog-error">${this._createViewError}</div>` : p}
            <div class="dialog-actions">
              <ha-button
                ?disabled=${this._creatingView}
                @click=${() => this._closeCreateViewDialog()}
              >
                Cancel
              </ha-button>
              <ha-button
                raised
                ?disabled=${!e || this._creatingView}
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
    var s;
    if (!this._editingView || !this._config) return p;
    const t = this._isCustomLayout() ? Math.max(1, this._editingView.widgets.length + 1) : ((s = this._config.layout_types[this._editingView.layout]) == null ? void 0 : s.slots) || 4;
    return h`
      <div class="editor-header">
        <ha-icon-button
          .path=${"M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z"}
          @click=${() => this._page = "main"}
        ></ha-icon-button>
        <ha-input
          .value=${this._editingView.name}
          @input=${(i) => this._updateEditingView({
      name: i.target.value
    })}
          placeholder="View name"
        ></ha-input>
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
              ${this._previewLoading ? h`<div class="preview-placeholder">
                    <ha-circular-progress indeterminate></ha-circular-progress>
                  </div>` : this._previewImage ? h`<img
                      class="preview-image"
                      src="data:image/png;base64,${this._previewImage}"
                      alt="Preview"
                    />` : h`<div class="preview-placeholder">No preview</div>`}
            </div>
          </ha-card>
        </div>

        <!-- Layout picker -->
        <div class="layout-section">
          <span class="layout-section-label">Layout</span>
          <div class="layout-picker">
            ${Object.entries(this._config.layout_types).map(
      ([i, r]) => {
        var a;
        return h`
                <button
                  class="layout-option ${((a = this._editingView) == null ? void 0 : a.layout) === i ? "selected" : ""}"
                  @click=${() => this._updateEditingView({ layout: i })}
                  title="${r.name} (${r.slots} slots)"
                >
                  ${this._renderLayoutIcon(i)}
                </button>
              `;
      }
    )}
          </div>
        </div>

        <!-- Widget slots -->
        <div class="section-title">Widgets</div>
        <div class="slots-grid">
          ${Array.from(
      { length: t },
      (i, r) => this._renderSlotEditor(r, t)
    )}
        </div>

        <!-- Theme selector -->
        <div class="form-row">
          <ha-select
            label="Theme"
            .value=${this._editingView.theme}
            .options=${_e(this._config.themes)}
            @selected=${(i) => {
      const r = P(
        i.detail,
        Object.keys(this._config.themes)
      );
      r && this._updateEditingView({ theme: r });
    }}
            @closed=${(i) => i.stopPropagation()}
          >
            ${Object.entries(this._config.themes).map(
      ([i, r]) => h`
                <mwc-list-item value=${i}>${r}</mwc-list-item>
              `
    )}
          </ha-select>
        </div>

        <!-- Background settings -->
        <div class="section-title">Background</div>
        <div class="background-section">
          <ha-input
            label="Background image path (optional)"
            .value=${this._editingView.background_image || ""}
            @input=${(i) => this._updateEditingView({
      background_image: i.target.value
    })}
            placeholder="/config/www/geekmagic/background.png"
          ></ha-input>
          <ha-select
            label="Background fit"
            .value=${this._editingView.background_mode || "stretch"}
            .options=${[
      { value: "stretch", label: "Stretch" },
      { value: "contain", label: "Contain" },
      { value: "cover", label: "Cover" }
    ]}
            @selected=${(i) => {
      const r = P(
        i.detail,
        ["stretch", "contain", "cover"]
      );
      r && this._updateEditingView({ background_mode: r });
    }}
            @closed=${(i) => i.stopPropagation()}
          >
            <mwc-list-item value="stretch">Stretch</mwc-list-item>
            <mwc-list-item value="contain">Contain</mwc-list-item>
            <mwc-list-item value="cover">Cover</mwc-list-item>
          </ha-select>
          <ha-entity-picker
            label="Background entity (optional)"
            .hass=${this.hass}
            .value=${this._editingView.background_entity || ""}
            allow-custom-entity
            @value-changed=${(i) => this._updateEditingView({
      background_entity: i.detail.value
    })}
          ></ha-entity-picker>
          <div class="field-help">
            Pick a sensor whose state is an image file path. It overrides the
            static path above when the state is valid.
          </div>
        </div>

        <!-- Display options -->
        <div class="section-title">Display options</div>
        <div class="display-options-section">
          <div class="slider-field">
            <label>Widget contrast: ${Math.round(
      (this._editingView.widget_contrast ?? 0.5) * 100
    )}%</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              .value=${String(this._editingView.widget_contrast ?? 0.5)}
              @input=${(i) => this._updateEditingView({
      widget_contrast: parseFloat(
        i.target.value
      )
    })}
            />
            <div class="field-help">
              Darken the area behind each widget to make text readable over
              busy backgrounds. 0% = fully transparent, 100% = fully opaque.
            </div>
          </div>
          <div class="slider-field">
            <label>Text opacity: ${Math.round(
      (this._editingView.text_opacity ?? 1) * 100
    )}%</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              .value=${String(this._editingView.text_opacity ?? 1)}
              @input=${(i) => this._updateEditingView({
      text_opacity: parseFloat(
        i.target.value
      )
    })}
            />
            <div class="field-help">
              How solid the text and icons appear. Lower values let the
              background photo shine through the letters. 100% = fully opaque.
            </div>
          </div>
        </div>
      </div>
    `;
  }
  _renderSlotEditor(e, t) {
    var g;
    if (!this._config || !this._editingView) return p;
    const s = this._isCustomLayout(), i = this._editingView.widgets, r = s && e === i.length, a = s ? i[e] : this._editingView.widgets.find((c) => c.slot === e), n = (a == null ? void 0 : a.type) || "", l = this._config.widget_types[n], d = this._editingView.layout;
    return r ? h`
        <ha-card class="slot-card">
          <div class="card-content">
            <div class="slot-header">
              <span style="flex: 1;">Add Widget</span>
            </div>
            <div class="slot-field">
              <ha-select
                label="Widget Type"
                .value=""
                .options=${de(
      "-- Empty --",
      Object.fromEntries(
        Object.entries(this._config.widget_types).map(
          ([c, u]) => [c, u.name]
        )
      )
    )}
                @selected=${(c) => {
      const u = ["", ...Object.keys(this._config.widget_types)], f = P(c.detail, u) ?? "";
      f && this._updateWidget(e, { type: f });
    }}
                @closed=${(c) => c.stopPropagation()}
              >
                <mwc-list-item value="">-- Empty --</mwc-list-item>
                ${Object.entries(this._config.widget_types).map(
      ([c, u]) => h`
                    <mwc-list-item value=${c}>${u.name}</mwc-list-item>
                  `
    )}
              </ha-select>
            </div>
          </div>
        </ha-card>
      ` : h`
      <ha-card class="slot-card">
        <div class="card-content">
          <div class="slot-header">
            ${s ? p : this._renderPositionGrid(e, t, d)}
            <span style="flex: 1;">
              ${s ? `Widget ${e + 1}` : `Slot ${e + 1}`}
            </span>
            ${s ? h`
                  <ha-icon-button
                    .path=${"M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"}
                    @click=${() => this._removeCustomWidget(e)}
                  ></ha-icon-button>
                ` : p}
          </div>

          <div class="slot-field">
            <ha-select
              label="Widget Type"
              .value=${n}
              .options=${de(
      "-- Empty --",
      Object.fromEntries(
        Object.entries(this._config.widget_types).map(
          ([c, u]) => [c, u.name]
        )
      )
    )}
              @selected=${(c) => {
      const u = ["", ...Object.keys(this._config.widget_types)], f = P(c.detail, u) ?? "";
      this._updateWidget(e, { type: f });
    }}
              @closed=${(c) => c.stopPropagation()}
            >
              <mwc-list-item value="">-- Empty --</mwc-list-item>
              ${Object.entries(this._config.widget_types).map(
      ([c, u]) => h`
                  <mwc-list-item value=${c}>${u.name}</mwc-list-item>
                `
    )}
            </ha-select>
          </div>

          ${l != null && l.needs_entity ? h`
                <div class="slot-field">
                  <ha-selector
                    .hass=${this.hass}
                    .selector=${{
      entity: l.entity_domains ? { domain: l.entity_domains } : {}
    }}
                    .value=${(a == null ? void 0 : a.entity_id) || ""}
                    .label=${"Entity"}
                    @value-changed=${(c) => this._updateWidget(e, {
      entity_id: c.detail.value
    })}
                  ></ha-selector>
                </div>
              ` : p}

          <div class="slot-field">
            <ha-input
              label="Label (optional)"
              .value=${(a == null ? void 0 : a.label) || ""}
              @input=${(c) => this._updateWidget(e, {
      label: c.target.value
    })}
            ></ha-input>
          </div>

          <div class="slot-field">
            <ha-input
              label="Text scale"
              type="number"
              min="0.5"
              max="3"
              step="0.1"
              .value=${String((a == null ? void 0 : a.text_scale) ?? 1)}
              @input=${(c) => this._updateWidget(e, {
      text_scale: parseFloat(c.target.value) || 1
    })}
            ></ha-input>
          </div>

          ${s ? h`
                <div class="slot-field custom-coords-row">
                  <ha-input
                    label="X"
                    type="number"
                    .value=${String((a == null ? void 0 : a.x) ?? 0)}
                    @input=${(c) => this._updateWidget(e, {
      x: parseInt(c.target.value, 10) || 0
    })}
                  ></ha-input>
                  <ha-input
                    label="Y"
                    type="number"
                    .value=${String((a == null ? void 0 : a.y) ?? 0)}
                    @input=${(c) => this._updateWidget(e, {
      y: parseInt(c.target.value, 10) || 0
    })}
                  ></ha-input>
                </div>
                <div class="slot-field custom-coords-row">
                  <ha-input
                    label="W"
                    type="number"
                    .value=${String((a == null ? void 0 : a.width) ?? 240)}
                    @input=${(c) => this._updateWidget(e, {
      width: parseInt(c.target.value, 10) || 240
    })}
                  ></ha-input>
                  <ha-input
                    label="H"
                    type="number"
                    .value=${String((a == null ? void 0 : a.height) ?? 240)}
                    @input=${(c) => this._updateWidget(e, {
      height: parseInt(c.target.value, 10) || 240
    })}
                  ></ha-input>
                </div>
              ` : p}

          ${(g = l == null ? void 0 : l.options) != null && g.length ? h`
                <div class="widget-options">
                  ${l.options.map(
      (c) => this._renderOptionField(e, a, c)
    )}
                </div>
              ` : p}
        </div>
      </ha-card>
    `;
  }
  _removeCustomWidget(e) {
    if (!this._editingView) return;
    const t = [...this._editingView.widgets];
    t.splice(e, 1), this._editingView = {
      ...this._editingView,
      widgets: t.map((s, i) => ({ ...s, slot: i }))
    }, this.requestUpdate(), this._refreshPreview();
  }
  _renderOptionField(e, t, s) {
    var r, a;
    const i = ((r = t == null ? void 0 : t.options) == null ? void 0 : r[s.key]) ?? s.default;
    switch (s.type) {
      case "boolean":
        return h`
          <div class="option-row">
            <label>${s.label}</label>
            <ha-switch
              .checked=${!!i}
              @change=${(n) => this._updateWidgetOption(
          e,
          s.key,
          n.target.checked
        )}
            ></ha-switch>
          </div>
        `;
      case "select":
        return h`
          <div class="option-field">
            <ha-select
              .label=${s.label}
              .value=${i || s.default || ""}
              .options=${s.options || []}
              @selected=${(n) => {
          const l = P(
            n.detail,
            s.options || []
          );
          l !== void 0 && this._updateWidgetOption(e, s.key, l);
        }}
              @closed=${(n) => n.stopPropagation()}
            >
              ${(a = s.options) == null ? void 0 : a.map(
          (n) => h`<mwc-list-item value=${n}>${n}</mwc-list-item>`
        )}
            </ha-select>
          </div>
        `;
      case "number":
        return h`
          <div class="option-field">
            <ha-input
              type="number"
              .label=${s.label}
              .value=${i !== void 0 ? String(i) : ""}
              .min=${s.min !== void 0 ? String(s.min) : ""}
              .max=${s.max !== void 0 ? String(s.max) : ""}
              @input=${(n) => {
          const l = n.target.value;
          this._updateWidgetOption(
            e,
            s.key,
            l ? parseFloat(l) : void 0
          );
        }}
            ></ha-input>
          </div>
        `;
      case "text":
        return h`
          <div class="option-field">
            <ha-input
              .label=${s.label}
              .value=${i || ""}
              .placeholder=${s.placeholder || ""}
              @input=${(n) => this._updateWidgetOption(
          e,
          s.key,
          n.target.value
        )}
            ></ha-input>
          </div>
        `;
      case "icon":
        return h`
          <div class="option-field">
            <ha-icon-picker
              .hass=${this.hass}
              .label=${s.label}
              .value=${i || ""}
              @value-changed=${(n) => this._updateWidgetOption(e, s.key, n.detail.value)}
            ></ha-icon-picker>
          </div>
        `;
      case "color":
        return h`
          <div class="option-field">
            <ha-selector
              .hass=${this.hass}
              .selector=${{ color_rgb: {} }}
              .value=${i}
              .label=${s.label}
              @value-changed=${(n) => this._updateWidgetOption(e, s.key, n.detail.value)}
            ></ha-selector>
            <div class="color-hex-input">
              <div
                class="color-preview-swatch"
                style="background-color: ${N(i)}"
              ></div>
              <ha-input
                .value=${N(i)}
                .label=${"Hex (fallback)"}
                placeholder="#FF5500 or 255,85,0"
                @change=${(n) => {
          const l = ce(
            n.target.value
          );
          l && this._updateWidgetOption(e, s.key, l);
        }}
              ></ha-input>
            </div>
          </div>
        `;
      case "entity":
        return h`
          <div class="option-field">
            <ha-selector
              .hass=${this.hass}
              .selector=${{ entity: {} }}
              .value=${i || ""}
              .label=${s.label}
              @value-changed=${(n) => this._updateWidgetOption(e, s.key, n.detail.value)}
            ></ha-selector>
          </div>
        `;
      case "thresholds":
        return this._renderThresholdsEditor(e, s.key, i);
      case "progress_items":
        return this._renderProgressItemsEditor(e, s.key, i);
      case "status_entities":
        return this._renderStatusEntitiesEditor(e, s.key, i);
      case "timezone":
        return h`
          <div class="option-field">
            <ha-combo-box
              .hass=${this.hass}
              .label=${s.label}
              .value=${i || ""}
              .items=${je.map((n) => ({ value: n, label: n }))}
              item-value-path="value"
              item-label-path="label"
              allow-custom-value
              @value-changed=${(n) => this._updateWidgetOption(e, s.key, n.detail.value)}
            ></ha-combo-box>
          </div>
        `;
      default:
        return p;
    }
  }
  _updateWidgetOption(e, t, s) {
    if (!this._editingView) return;
    const i = [...this._editingView.widgets], r = i.findIndex((a) => a.slot === e);
    if (r >= 0) {
      const a = i[r];
      i[r] = {
        ...a,
        options: { ...a.options || {}, [t]: s }
      };
    } else
      i.push({
        slot: e,
        type: "",
        options: { [t]: s }
      });
    this._editingView = { ...this._editingView, widgets: [...i] }, this.requestUpdate(), this._refreshPreview();
  }
  _renderThresholdsEditor(e, t, s) {
    const i = s || [];
    return h`
      <div class="option-field">
        <div class="array-editor">
          <div class="array-editor-header">
            <span>Color Thresholds</span>
          </div>
          <div class="array-items">
            ${i.map(
      (r, a) => h`
                <div class="threshold-item-container">
                  <div class="threshold-item">
                    <ha-input
                      class="threshold-value"
                      type="number"
                      label="Value"
                      .value=${String(r.value)}
                      @input=${(n) => {
        const l = [...i];
        l[a] = {
          ...r,
          value: parseFloat(n.target.value) || 0
        }, this._updateWidgetOption(e, t, l);
      }}
                    ></ha-input>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ color_rgb: {} }}
                      .value=${r.color}
                      @value-changed=${(n) => {
        const l = [...i];
        l[a] = { ...r, color: n.detail.value }, this._updateWidgetOption(e, t, l);
      }}
                    ></ha-selector>
                    <ha-icon-button
                      .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                      @click=${() => {
        const n = i.filter((l, d) => d !== a);
        this._updateWidgetOption(e, t, n);
      }}
                    ></ha-icon-button>
                  </div>
                  <div class="threshold-hex-row">
                    <div
                      class="color-preview-swatch"
                      style="background-color: ${N(r.color)}"
                    ></div>
                    <ha-input
                      class="threshold-hex-input"
                      .value=${N(r.color)}
                      label="Hex (fallback)"
                      placeholder="#FF5500"
                      @change=${(n) => {
        const l = ce(
          n.target.value
        );
        if (l) {
          const d = [...i];
          d[a] = { ...r, color: l }, this._updateWidgetOption(e, t, d);
        }
      }}
                    ></ha-input>
                  </div>
                </div>
              `
    )}
            <div
              class="add-item-button"
              @click=${() => {
      const r = [...i, { value: 0, color: [255, 255, 0] }];
      this._updateWidgetOption(e, t, r);
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
  _renderProgressItemsEditor(e, t, s) {
    const i = s || [];
    return h`
      <div class="option-field">
        <div class="array-editor">
          <div class="array-editor-header">
            <span>Progress Items (${i.length})</span>
          </div>
          <div class="array-items">
            ${i.map((r, a) => {
      const n = `${e}-progress-${a}`, l = this._expandedItems.has(n);
      return h`
                <div class="array-item">
                  <div
                    class="array-item-header"
                    @click=${() => this._toggleItemExpanded(n)}
                  >
                    <span class="array-item-title">
                      ${r.label || r.entity_id || `Item ${a + 1}`}
                    </span>
                    <div class="array-item-actions">
                      <ha-icon-button
                        .path=${a > 0 ? "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z" : ""}
                        @click=${(d) => {
        d.stopPropagation(), a > 0 && this._moveArrayItem(e, t, i, a, -1);
      }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${a < i.length - 1 ? "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z" : ""}
                        @click=${(d) => {
        d.stopPropagation(), a < i.length - 1 && this._moveArrayItem(e, t, i, a, 1);
      }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                        @click=${(d) => {
        d.stopPropagation();
        const g = i.filter((c, u) => u !== a);
        this._updateWidgetOption(e, t, g);
      }}
                      ></ha-icon-button>
                    </div>
                  </div>
                  <div class="array-item-content ${l ? "" : "collapsed"}">
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ entity: {} }}
                      .value=${r.entity_id || ""}
                      .label=${"Entity"}
                      @value-changed=${(d) => this._updateArrayItem(e, t, i, a, {
        entity_id: d.detail.value
      })}
                    ></ha-selector>
                    <ha-input
                      label="Label"
                      .value=${r.label || ""}
                      @input=${(d) => this._updateArrayItem(e, t, i, a, {
        label: d.target.value
      })}
                    ></ha-input>
                    <ha-input
                      type="number"
                      label="Target"
                      .value=${r.target !== void 0 ? String(r.target) : "100"}
                      @input=${(d) => this._updateArrayItem(e, t, i, a, {
        target: parseFloat(d.target.value) || 100
      })}
                    ></ha-input>
                    <ha-icon-picker
                      .hass=${this.hass}
                      label="Icon"
                      .value=${r.icon || ""}
                      @value-changed=${(d) => this._updateArrayItem(e, t, i, a, {
        icon: d.detail.value
      })}
                    ></ha-icon-picker>
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ color_rgb: {} }}
                      .value=${r.color}
                      .label=${"Color"}
                      @value-changed=${(d) => this._updateArrayItem(e, t, i, a, {
        color: d.detail.value
      })}
                    ></ha-selector>
                  </div>
                </div>
              `;
    })}
            <div
              class="add-item-button"
              @click=${() => {
      const r = [...i, { entity_id: "", target: 100 }];
      this._updateWidgetOption(e, t, r), this._expandedItems.add(`${e}-progress-${r.length - 1}`), this.requestUpdate();
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
  _renderStatusEntitiesEditor(e, t, s) {
    const i = s || [];
    return h`
      <div class="option-field">
        <div class="array-editor">
          <div class="array-editor-header">
            <span>Status Entities (${i.length})</span>
          </div>
          <div class="array-items">
            ${i.map((r, a) => {
      const n = `${e}-status-${a}`, l = this._expandedItems.has(n);
      return h`
                <div class="array-item">
                  <div
                    class="array-item-header"
                    @click=${() => this._toggleItemExpanded(n)}
                  >
                    <span class="array-item-title">
                      ${r.label || r.entity_id || `Entity ${a + 1}`}
                    </span>
                    <div class="array-item-actions">
                      <ha-icon-button
                        .path=${a > 0 ? "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z" : ""}
                        @click=${(d) => {
        d.stopPropagation(), a > 0 && this._moveArrayItem(e, t, i, a, -1);
      }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${a < i.length - 1 ? "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z" : ""}
                        @click=${(d) => {
        d.stopPropagation(), a < i.length - 1 && this._moveArrayItem(e, t, i, a, 1);
      }}
                      ></ha-icon-button>
                      <ha-icon-button
                        .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                        @click=${(d) => {
        d.stopPropagation();
        const g = i.filter((c, u) => u !== a);
        this._updateWidgetOption(e, t, g);
      }}
                      ></ha-icon-button>
                    </div>
                  </div>
                  <div class="array-item-content ${l ? "" : "collapsed"}">
                    <ha-selector
                      .hass=${this.hass}
                      .selector=${{ entity: {} }}
                      .value=${r.entity_id || ""}
                      .label=${"Entity"}
                      @value-changed=${(d) => this._updateArrayItem(e, t, i, a, {
        entity_id: d.detail.value
      })}
                    ></ha-selector>
                    <ha-input
                      label="Label"
                      .value=${r.label || ""}
                      @input=${(d) => this._updateArrayItem(e, t, i, a, {
        label: d.target.value
      })}
                    ></ha-input>
                    <ha-icon-picker
                      .hass=${this.hass}
                      label="Icon"
                      .value=${r.icon || ""}
                      @value-changed=${(d) => this._updateArrayItem(e, t, i, a, {
        icon: d.detail.value
      })}
                    ></ha-icon-picker>
                  </div>
                </div>
              `;
    })}
            <div
              class="add-item-button"
              @click=${() => {
      const r = [...i, { entity_id: "" }];
      this._updateWidgetOption(e, t, r), this._expandedItems.add(`${e}-status-${r.length - 1}`), this.requestUpdate();
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
  _toggleItemExpanded(e) {
    this._expandedItems.has(e) ? this._expandedItems.delete(e) : this._expandedItems.add(e), this._expandedItems = new Set(this._expandedItems);
  }
  _updateArrayItem(e, t, s, i, r) {
    const a = [...s];
    a[i] = { ...a[i], ...r }, this._updateWidgetOption(e, t, a);
  }
  _moveArrayItem(e, t, s, i, r) {
    const a = i + r;
    if (a < 0 || a >= s.length) return;
    const n = [...s];
    [n[i], n[a]] = [n[a], n[i]], this._updateWidgetOption(e, t, n);
  }
  _renderPositionGrid(e, t, s) {
    let i = 2, r = !1;
    switch (s) {
      case "fullscreen":
        i = 1;
        break;
      case "grid_2x2":
        i = 2;
        break;
      case "grid_2x3":
        i = 3;
        break;
      case "grid_3x2":
        i = 2;
        break;
      case "hero":
        i = 3, r = !0;
        break;
      case "split":
        i = 2;
        break;
      case "three_column":
        i = 3;
        break;
      default:
        i = 2;
    }
    const a = [];
    if (r) {
      a.push(h`
        <div
          class="position-cell hero-main ${e === 0 ? "active" : ""}"
          @click=${() => this._swapSlots(e, 0)}
          title="Hero (main)"
        ></div>
      `);
      for (let n = 1; n <= 3; n++)
        a.push(h`
          <div
            class="position-cell ${e === n ? "active" : ""}"
            @click=${() => this._swapSlots(e, n)}
            title="Footer ${n}"
          ></div>
        `);
    } else
      for (let n = 0; n < t; n++)
        a.push(h`
          <div
            class="position-cell ${e === n ? "active" : ""}"
            @click=${() => this._swapSlots(e, n)}
            title="Slot ${n + 1}"
          ></div>
        `);
    return h`
      <div class="position-grid cols-${i}">${a}</div>
    `;
  }
  _renderLayoutIcon(e) {
    if (e === "custom")
      return h`
        <div class="layout-icon custom-layout-icon">
          <svg viewBox="0 0 24 24" width="24" height="24">
            <path
              fill="currentColor"
              d="M13,17H17V13H19V17H23V19H19V23H17V19H13V17M11,17V19H9V17H11M7,17V19H5V17H7M19,9V11H17V9H19M19,5V7H17V5H19M15,5V7H13V5H15M11,5V7H9V5H11M7,5V7H5V5H7M7,13V15H5V13H7M7,9V11H5V9H7Z"
            />
          </svg>
        </div>
      `;
    const s = {
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
    }[e] || { cls: "", cells: 4 }, i = Array.from({ length: s.cells }, () => h`<div></div>`);
    return h`<div class="layout-icon ${s.cls}">${i}</div>`;
  }
  _swapSlots(e, t) {
    if (e === t || !this._editingView) return;
    const s = [...this._editingView.widgets], i = s.find((a) => a.slot === e), r = s.find((a) => a.slot === t);
    i && (i.slot = t), r && (r.slot = e), this._editingView = { ...this._editingView, widgets: [...s] }, this.requestUpdate(), this._refreshPreview();
  }
};
X.styles = ye`
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

    .editor-header ha-input {
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

    .background-section {
      display: grid;
      gap: 16px;
      margin-bottom: 16px;
    }

    .background-section ha-input,
    .background-section ha-select {
      width: 100%;
    }

    .field-help {
      font-size: 12px;
      color: var(--secondary-text-color);
      line-height: 1.4;
      margin-top: -8px;
    }

    .slider-field {
      margin-bottom: 16px;
    }

    .slider-field label {
      display: block;
      margin-bottom: 8px;
      color: var(--primary-text-color);
    }

    .slider-field input[type="range"] {
      display: block;
      width: 100%;
    }

    .slider-field .field-help {
      margin-top: 8px;
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
      margin-bottom: 24px;
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

    .custom-layout-icon {
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .custom-layout-icon svg {
      width: 24px;
      height: 24px;
      color: var(--primary-text-color);
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

    .custom-coords-row {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }

    .custom-coords-row ha-input {
      min-width: 0;
    }

    ha-select,
    ha-input {
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

    .threshold-hex-input {
      flex: 1;
    }

    /* Color hex input fallback (Safari compatibility) */
    .color-hex-input {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 8px;
    }

    .color-hex-input ha-input {
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
let v = X;
m([
  U({ attribute: !1 })
], v.prototype, "hass");
m([
  U({ type: Boolean })
], v.prototype, "narrow");
m([
  U({ attribute: !1 })
], v.prototype, "route");
m([
  U({ attribute: !1 })
], v.prototype, "panel");
m([
  _()
], v.prototype, "_page");
m([
  _()
], v.prototype, "_config");
m([
  _()
], v.prototype, "_views");
m([
  _()
], v.prototype, "_devices");
m([
  _()
], v.prototype, "_editingView");
m([
  _()
], v.prototype, "_previewImage");
m([
  _()
], v.prototype, "_previewLoading");
m([
  _()
], v.prototype, "_loading");
m([
  _()
], v.prototype, "_saving");
m([
  _()
], v.prototype, "_expandedItems");
m([
  _()
], v.prototype, "_viewPreviews");
m([
  _()
], v.prototype, "_createViewDialogOpen");
m([
  _()
], v.prototype, "_newViewName");
m([
  _()
], v.prototype, "_creatingView");
m([
  _()
], v.prototype, "_createViewError");
customElements.get("geekmagic-panel") || customElements.define("geekmagic-panel", v);
export {
  v as GeekMagicPanel
};
