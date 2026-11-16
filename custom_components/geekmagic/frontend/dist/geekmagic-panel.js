/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const ce = globalThis, we = ce.ShadowRoot && (ce.ShadyCSS === void 0 || ce.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, xe = Symbol(), Se = /* @__PURE__ */ new WeakMap();
let Ze = class {
  constructor(e, i, s) {
    if (this._$cssResult$ = !0, s !== xe) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = e, this.t = i;
  }
  get styleSheet() {
    let e = this.o;
    const i = this.t;
    if (we && e === void 0) {
      const s = i !== void 0 && i.length === 1;
      s && (e = Se.get(i)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), s && Se.set(i, e));
    }
    return e;
  }
  toString() {
    return this.cssText;
  }
};
const lt = (t) => new Ze(typeof t == "string" ? t : t + "", void 0, xe), P = (t, ...e) => {
  const i = t.length === 1 ? t[0] : e.reduce((s, r, a) => s + ((n) => {
    if (n._$cssResult$ === !0) return n.cssText;
    if (typeof n == "number") return n;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + n + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(r) + t[a + 1], t[0]);
  return new Ze(i, t, xe);
}, ct = (t, e) => {
  if (we) t.adoptedStyleSheets = e.map((i) => i instanceof CSSStyleSheet ? i : i.styleSheet);
  else for (const i of e) {
    const s = document.createElement("style"), r = ce.litNonce;
    r !== void 0 && s.setAttribute("nonce", r), s.textContent = i.cssText, t.appendChild(s);
  }
}, Ce = we ? (t) => t : (t) => t instanceof CSSStyleSheet ? ((e) => {
  let i = "";
  for (const s of e.cssRules) i += s.cssText;
  return lt(i);
})(t) : t;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: ht, defineProperty: dt, getOwnPropertyDescriptor: pt, getOwnPropertyNames: ut, getOwnPropertySymbols: gt, getPrototypeOf: mt } = Object, M = globalThis, Oe = M.trustedTypes, vt = Oe ? Oe.emptyScript : "", ue = M.reactiveElementPolyfillSupport, K = (t, e) => t, he = { toAttribute(t, e) {
  switch (e) {
    case Boolean:
      t = t ? vt : null;
      break;
    case Object:
    case Array:
      t = t == null ? t : JSON.stringify(t);
  }
  return t;
}, fromAttribute(t, e) {
  let i = t;
  switch (e) {
    case Boolean:
      i = t !== null;
      break;
    case Number:
      i = t === null ? null : Number(t);
      break;
    case Object:
    case Array:
      try {
        i = JSON.parse(t);
      } catch {
        i = null;
      }
  }
  return i;
} }, ke = (t, e) => !ht(t, e), Te = { attribute: !0, type: String, converter: he, reflect: !1, useDefault: !1, hasChanged: ke };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), M.litPropertyMetadata ?? (M.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let B = class extends HTMLElement {
  static addInitializer(e) {
    this._$Ei(), (this.l ?? (this.l = [])).push(e);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(e, i = Te) {
    if (i.state && (i.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((i = Object.create(i)).wrapped = !0), this.elementProperties.set(e, i), !i.noAccessor) {
      const s = Symbol(), r = this.getPropertyDescriptor(e, s, i);
      r !== void 0 && dt(this.prototype, e, r);
    }
  }
  static getPropertyDescriptor(e, i, s) {
    const { get: r, set: a } = pt(this.prototype, e) ?? { get() {
      return this[i];
    }, set(n) {
      this[i] = n;
    } };
    return { get: r, set(n) {
      const c = r == null ? void 0 : r.call(this);
      a == null || a.call(this, n), this.requestUpdate(e, c, s);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(e) {
    return this.elementProperties.get(e) ?? Te;
  }
  static _$Ei() {
    if (this.hasOwnProperty(K("elementProperties"))) return;
    const e = mt(this);
    e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(K("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(K("properties"))) {
      const i = this.properties, s = [...ut(i), ...gt(i)];
      for (const r of s) this.createProperty(r, i[r]);
    }
    const e = this[Symbol.metadata];
    if (e !== null) {
      const i = litPropertyMetadata.get(e);
      if (i !== void 0) for (const [s, r] of i) this.elementProperties.set(s, r);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [i, s] of this.elementProperties) {
      const r = this._$Eu(i, s);
      r !== void 0 && this._$Eh.set(r, i);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(e) {
    const i = [];
    if (Array.isArray(e)) {
      const s = new Set(e.flat(1 / 0).reverse());
      for (const r of s) i.unshift(Ce(r));
    } else e !== void 0 && i.push(Ce(e));
    return i;
  }
  static _$Eu(e, i) {
    const s = i.attribute;
    return s === !1 ? void 0 : typeof s == "string" ? s : typeof e == "string" ? e.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    var e;
    this._$ES = new Promise((i) => this.enableUpdating = i), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), (e = this.constructor.l) == null || e.forEach((i) => i(this));
  }
  addController(e) {
    var i;
    (this._$EO ?? (this._$EO = /* @__PURE__ */ new Set())).add(e), this.renderRoot !== void 0 && this.isConnected && ((i = e.hostConnected) == null || i.call(e));
  }
  removeController(e) {
    var i;
    (i = this._$EO) == null || i.delete(e);
  }
  _$E_() {
    const e = /* @__PURE__ */ new Map(), i = this.constructor.elementProperties;
    for (const s of i.keys()) this.hasOwnProperty(s) && (e.set(s, this[s]), delete this[s]);
    e.size > 0 && (this._$Ep = e);
  }
  createRenderRoot() {
    const e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return ct(e, this.constructor.elementStyles), e;
  }
  connectedCallback() {
    var e;
    this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this.enableUpdating(!0), (e = this._$EO) == null || e.forEach((i) => {
      var s;
      return (s = i.hostConnected) == null ? void 0 : s.call(i);
    });
  }
  enableUpdating(e) {
  }
  disconnectedCallback() {
    var e;
    (e = this._$EO) == null || e.forEach((i) => {
      var s;
      return (s = i.hostDisconnected) == null ? void 0 : s.call(i);
    });
  }
  attributeChangedCallback(e, i, s) {
    this._$AK(e, s);
  }
  _$ET(e, i) {
    var a;
    const s = this.constructor.elementProperties.get(e), r = this.constructor._$Eu(e, s);
    if (r !== void 0 && s.reflect === !0) {
      const n = (((a = s.converter) == null ? void 0 : a.toAttribute) !== void 0 ? s.converter : he).toAttribute(i, s.type);
      this._$Em = e, n == null ? this.removeAttribute(r) : this.setAttribute(r, n), this._$Em = null;
    }
  }
  _$AK(e, i) {
    var a, n;
    const s = this.constructor, r = s._$Eh.get(e);
    if (r !== void 0 && this._$Em !== r) {
      const c = s.getPropertyOptions(r), l = typeof c.converter == "function" ? { fromAttribute: c.converter } : ((a = c.converter) == null ? void 0 : a.fromAttribute) !== void 0 ? c.converter : he;
      this._$Em = r;
      const h = l.fromAttribute(i, c.type);
      this[r] = h ?? ((n = this._$Ej) == null ? void 0 : n.get(r)) ?? h, this._$Em = null;
    }
  }
  requestUpdate(e, i, s) {
    var r;
    if (e !== void 0) {
      const a = this.constructor, n = this[e];
      if (s ?? (s = a.getPropertyOptions(e)), !((s.hasChanged ?? ke)(n, i) || s.useDefault && s.reflect && n === ((r = this._$Ej) == null ? void 0 : r.get(e)) && !this.hasAttribute(a._$Eu(e, s)))) return;
      this.C(e, i, s);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(e, i, { useDefault: s, reflect: r, wrapped: a }, n) {
    s && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(e) && (this._$Ej.set(e, n ?? i ?? this[e]), a !== !0 || n !== void 0) || (this._$AL.has(e) || (this.hasUpdated || s || (i = void 0), this._$AL.set(e, i)), r === !0 && this._$Em !== e && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(e));
  }
  async _$EP() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (i) {
      Promise.reject(i);
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
        for (const [a, n] of this._$Ep) this[a] = n;
        this._$Ep = void 0;
      }
      const r = this.constructor.elementProperties;
      if (r.size > 0) for (const [a, n] of r) {
        const { wrapped: c } = n, l = this[a];
        c !== !0 || this._$AL.has(a) || l === void 0 || this.C(a, void 0, n, l);
      }
    }
    let e = !1;
    const i = this._$AL;
    try {
      e = this.shouldUpdate(i), e ? (this.willUpdate(i), (s = this._$EO) == null || s.forEach((r) => {
        var a;
        return (a = r.hostUpdate) == null ? void 0 : a.call(r);
      }), this.update(i)) : this._$EM();
    } catch (r) {
      throw e = !1, this._$EM(), r;
    }
    e && this._$AE(i);
  }
  willUpdate(e) {
  }
  _$AE(e) {
    var i;
    (i = this._$EO) == null || i.forEach((s) => {
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
    this._$Eq && (this._$Eq = this._$Eq.forEach((i) => this._$ET(i, this[i]))), this._$EM();
  }
  updated(e) {
  }
  firstUpdated(e) {
  }
};
B.elementStyles = [], B.shadowRootOptions = { mode: "open" }, B[K("elementProperties")] = /* @__PURE__ */ new Map(), B[K("finalized")] = /* @__PURE__ */ new Map(), ue == null || ue({ ReactiveElement: B }), (M.reactiveElementVersions ?? (M.reactiveElementVersions = [])).push("2.1.1");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Y = globalThis, de = Y.trustedTypes, Pe = de ? de.createPolicy("lit-html", { createHTML: (t) => t }) : void 0, Je = "$lit$", z = `lit$${Math.random().toFixed(9).slice(2)}$`, Ke = "?" + z, _t = `<${Ke}>`, U = document, Q = () => U.createComment(""), X = (t) => t === null || typeof t != "object" && typeof t != "function", Ae = Array.isArray, ft = (t) => Ae(t) || typeof (t == null ? void 0 : t[Symbol.iterator]) == "function", ge = `[ 	
\f\r]`, Z = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, ze = /-->/g, Me = />/g, R = RegExp(`>|${ge}(?:([^\\s"'>=/]+)(${ge}*=${ge}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), Ne = /'/g, Le = /"/g, Ye = /^(?:script|style|textarea|title)$/i, Qe = (t) => (e, ...i) => ({ _$litType$: t, strings: e, values: i }), o = Qe(1), bt = Qe(2), G = Symbol.for("lit-noChange"), d = Symbol.for("lit-nothing"), Re = /* @__PURE__ */ new WeakMap(), D = U.createTreeWalker(U, 129);
function Xe(t, e) {
  if (!Ae(t) || !t.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return Pe !== void 0 ? Pe.createHTML(e) : e;
}
const yt = (t, e) => {
  const i = t.length - 1, s = [];
  let r, a = e === 2 ? "<svg>" : e === 3 ? "<math>" : "", n = Z;
  for (let c = 0; c < i; c++) {
    const l = t[c];
    let h, p, g = -1, f = 0;
    for (; f < l.length && (n.lastIndex = f, p = n.exec(l), p !== null); ) f = n.lastIndex, n === Z ? p[1] === "!--" ? n = ze : p[1] !== void 0 ? n = Me : p[2] !== void 0 ? (Ye.test(p[2]) && (r = RegExp("</" + p[2], "g")), n = R) : p[3] !== void 0 && (n = R) : n === R ? p[0] === ">" ? (n = r ?? Z, g = -1) : p[1] === void 0 ? g = -2 : (g = n.lastIndex - p[2].length, h = p[1], n = p[3] === void 0 ? R : p[3] === '"' ? Le : Ne) : n === Le || n === Ne ? n = R : n === ze || n === Me ? n = Z : (n = R, r = void 0);
    const k = n === R && t[c + 1].startsWith("/>") ? " " : "";
    a += n === Z ? l + _t : g >= 0 ? (s.push(h), l.slice(0, g) + Je + l.slice(g) + z + k) : l + z + (g === -2 ? c : k);
  }
  return [Xe(t, a + (t[i] || "<?>") + (e === 2 ? "</svg>" : e === 3 ? "</math>" : "")), s];
};
class ee {
  constructor({ strings: e, _$litType$: i }, s) {
    let r;
    this.parts = [];
    let a = 0, n = 0;
    const c = e.length - 1, l = this.parts, [h, p] = yt(e, i);
    if (this.el = ee.createElement(h, s), D.currentNode = this.el.content, i === 2 || i === 3) {
      const g = this.el.content.firstChild;
      g.replaceWith(...g.childNodes);
    }
    for (; (r = D.nextNode()) !== null && l.length < c; ) {
      if (r.nodeType === 1) {
        if (r.hasAttributes()) for (const g of r.getAttributeNames()) if (g.endsWith(Je)) {
          const f = p[n++], k = r.getAttribute(g).split(z), L = /([.?@])?(.*)/.exec(f);
          l.push({ type: 1, index: a, name: L[2], strings: k, ctor: L[1] === "." ? wt : L[1] === "?" ? xt : L[1] === "@" ? kt : pe }), r.removeAttribute(g);
        } else g.startsWith(z) && (l.push({ type: 6, index: a }), r.removeAttribute(g));
        if (Ye.test(r.tagName)) {
          const g = r.textContent.split(z), f = g.length - 1;
          if (f > 0) {
            r.textContent = de ? de.emptyScript : "";
            for (let k = 0; k < f; k++) r.append(g[k], Q()), D.nextNode(), l.push({ type: 2, index: ++a });
            r.append(g[f], Q());
          }
        }
      } else if (r.nodeType === 8) if (r.data === Ke) l.push({ type: 2, index: a });
      else {
        let g = -1;
        for (; (g = r.data.indexOf(z, g + 1)) !== -1; ) l.push({ type: 7, index: a }), g += z.length - 1;
      }
      a++;
    }
  }
  static createElement(e, i) {
    const s = U.createElement("template");
    return s.innerHTML = e, s;
  }
}
function W(t, e, i = t, s) {
  var n, c;
  if (e === G) return e;
  let r = s !== void 0 ? (n = i._$Co) == null ? void 0 : n[s] : i._$Cl;
  const a = X(e) ? void 0 : e._$litDirective$;
  return (r == null ? void 0 : r.constructor) !== a && ((c = r == null ? void 0 : r._$AO) == null || c.call(r, !1), a === void 0 ? r = void 0 : (r = new a(t), r._$AT(t, i, s)), s !== void 0 ? (i._$Co ?? (i._$Co = []))[s] = r : i._$Cl = r), r !== void 0 && (e = W(t, r._$AS(t, e.values), r, s)), e;
}
class $t {
  constructor(e, i) {
    this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = i;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(e) {
    const { el: { content: i }, parts: s } = this._$AD, r = ((e == null ? void 0 : e.creationScope) ?? U).importNode(i, !0);
    D.currentNode = r;
    let a = D.nextNode(), n = 0, c = 0, l = s[0];
    for (; l !== void 0; ) {
      if (n === l.index) {
        let h;
        l.type === 2 ? h = new se(a, a.nextSibling, this, e) : l.type === 1 ? h = new l.ctor(a, l.name, l.strings, this, e) : l.type === 6 && (h = new At(a, this, e)), this._$AV.push(h), l = s[++c];
      }
      n !== (l == null ? void 0 : l.index) && (a = D.nextNode(), n++);
    }
    return D.currentNode = U, r;
  }
  p(e) {
    let i = 0;
    for (const s of this._$AV) s !== void 0 && (s.strings !== void 0 ? (s._$AI(e, s, i), i += s.strings.length - 2) : s._$AI(e[i])), i++;
  }
}
class se {
  get _$AU() {
    var e;
    return ((e = this._$AM) == null ? void 0 : e._$AU) ?? this._$Cv;
  }
  constructor(e, i, s, r) {
    this.type = 2, this._$AH = d, this._$AN = void 0, this._$AA = e, this._$AB = i, this._$AM = s, this.options = r, this._$Cv = (r == null ? void 0 : r.isConnected) ?? !0;
  }
  get parentNode() {
    let e = this._$AA.parentNode;
    const i = this._$AM;
    return i !== void 0 && (e == null ? void 0 : e.nodeType) === 11 && (e = i.parentNode), e;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(e, i = this) {
    e = W(this, e, i), X(e) ? e === d || e == null || e === "" ? (this._$AH !== d && this._$AR(), this._$AH = d) : e !== this._$AH && e !== G && this._(e) : e._$litType$ !== void 0 ? this.$(e) : e.nodeType !== void 0 ? this.T(e) : ft(e) ? this.k(e) : this._(e);
  }
  O(e) {
    return this._$AA.parentNode.insertBefore(e, this._$AB);
  }
  T(e) {
    this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
  }
  _(e) {
    this._$AH !== d && X(this._$AH) ? this._$AA.nextSibling.data = e : this.T(U.createTextNode(e)), this._$AH = e;
  }
  $(e) {
    var a;
    const { values: i, _$litType$: s } = e, r = typeof s == "number" ? this._$AC(e) : (s.el === void 0 && (s.el = ee.createElement(Xe(s.h, s.h[0]), this.options)), s);
    if (((a = this._$AH) == null ? void 0 : a._$AD) === r) this._$AH.p(i);
    else {
      const n = new $t(r, this), c = n.u(this.options);
      n.p(i), this.T(c), this._$AH = n;
    }
  }
  _$AC(e) {
    let i = Re.get(e.strings);
    return i === void 0 && Re.set(e.strings, i = new ee(e)), i;
  }
  k(e) {
    Ae(this._$AH) || (this._$AH = [], this._$AR());
    const i = this._$AH;
    let s, r = 0;
    for (const a of e) r === i.length ? i.push(s = new se(this.O(Q()), this.O(Q()), this, this.options)) : s = i[r], s._$AI(a), r++;
    r < i.length && (this._$AR(s && s._$AB.nextSibling, r), i.length = r);
  }
  _$AR(e = this._$AA.nextSibling, i) {
    var s;
    for ((s = this._$AP) == null ? void 0 : s.call(this, !1, !0, i); e !== this._$AB; ) {
      const r = e.nextSibling;
      e.remove(), e = r;
    }
  }
  setConnected(e) {
    var i;
    this._$AM === void 0 && (this._$Cv = e, (i = this._$AP) == null || i.call(this, e));
  }
}
class pe {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(e, i, s, r, a) {
    this.type = 1, this._$AH = d, this._$AN = void 0, this.element = e, this.name = i, this._$AM = r, this.options = a, s.length > 2 || s[0] !== "" || s[1] !== "" ? (this._$AH = Array(s.length - 1).fill(new String()), this.strings = s) : this._$AH = d;
  }
  _$AI(e, i = this, s, r) {
    const a = this.strings;
    let n = !1;
    if (a === void 0) e = W(this, e, i, 0), n = !X(e) || e !== this._$AH && e !== G, n && (this._$AH = e);
    else {
      const c = e;
      let l, h;
      for (e = a[0], l = 0; l < a.length - 1; l++) h = W(this, c[s + l], i, l), h === G && (h = this._$AH[l]), n || (n = !X(h) || h !== this._$AH[l]), h === d ? e = d : e !== d && (e += (h ?? "") + a[l + 1]), this._$AH[l] = h;
    }
    n && !r && this.j(e);
  }
  j(e) {
    e === d ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
  }
}
class wt extends pe {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(e) {
    this.element[this.name] = e === d ? void 0 : e;
  }
}
class xt extends pe {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(e) {
    this.element.toggleAttribute(this.name, !!e && e !== d);
  }
}
class kt extends pe {
  constructor(e, i, s, r, a) {
    super(e, i, s, r, a), this.type = 5;
  }
  _$AI(e, i = this) {
    if ((e = W(this, e, i, 0) ?? d) === G) return;
    const s = this._$AH, r = e === d && s !== d || e.capture !== s.capture || e.once !== s.once || e.passive !== s.passive, a = e !== d && (s === d || r);
    r && this.element.removeEventListener(this.name, this, s), a && this.element.addEventListener(this.name, this, e), this._$AH = e;
  }
  handleEvent(e) {
    var i;
    typeof this._$AH == "function" ? this._$AH.call(((i = this.options) == null ? void 0 : i.host) ?? this.element, e) : this._$AH.handleEvent(e);
  }
}
class At {
  constructor(e, i, s) {
    this.element = e, this.type = 6, this._$AN = void 0, this._$AM = i, this.options = s;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(e) {
    W(this, e);
  }
}
const me = Y.litHtmlPolyfillSupport;
me == null || me(ee, se), (Y.litHtmlVersions ?? (Y.litHtmlVersions = [])).push("3.3.1");
const Et = (t, e, i) => {
  const s = (i == null ? void 0 : i.renderBefore) ?? e;
  let r = s._$litPart$;
  if (r === void 0) {
    const a = (i == null ? void 0 : i.renderBefore) ?? null;
    s._$litPart$ = r = new se(e.insertBefore(Q(), a), a, void 0, i ?? {});
  }
  return r._$AI(t), r;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const H = globalThis;
class E extends B {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    var i;
    const e = super.createRenderRoot();
    return (i = this.renderOptions).renderBefore ?? (i.renderBefore = e.firstChild), e;
  }
  update(e) {
    const i = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Et(i, this.renderRoot, this.renderOptions);
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
    return G;
  }
}
var We;
E._$litElement$ = !0, E.finalized = !0, (We = H.litElementHydrateSupport) == null || We.call(H, { LitElement: E });
const ve = H.litElementPolyfillSupport;
ve == null || ve({ LitElement: E });
(H.litElementVersions ?? (H.litElementVersions = [])).push("4.2.1");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const N = (t) => (e, i) => {
  i !== void 0 ? i.addInitializer(() => {
    customElements.define(t, e);
  }) : customElements.define(t, e);
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const St = { attribute: !0, type: String, converter: he, reflect: !1, hasChanged: ke }, Ct = (t = St, e, i) => {
  const { kind: s, metadata: r } = i;
  let a = globalThis.litPropertyMetadata.get(r);
  if (a === void 0 && globalThis.litPropertyMetadata.set(r, a = /* @__PURE__ */ new Map()), s === "setter" && ((t = Object.create(t)).wrapped = !0), a.set(i.name, t), s === "accessor") {
    const { name: n } = i;
    return { set(c) {
      const l = e.get.call(this);
      e.set.call(this, c), this.requestUpdate(n, l, t);
    }, init(c) {
      return c !== void 0 && this.C(n, void 0, t, c), c;
    } };
  }
  if (s === "setter") {
    const { name: n } = i;
    return function(c) {
      const l = this[n];
      e.call(this, c), this.requestUpdate(n, l, t);
    };
  }
  throw Error("Unsupported decorator location: " + s);
};
function m(t) {
  return (e, i) => typeof i == "object" ? Ct(t, e, i) : ((s, r, a) => {
    const n = r.hasOwnProperty(a);
    return r.constructor.createProperty(a, s), n ? Object.getOwnPropertyDescriptor(r, a) : void 0;
  })(t, e, i);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function u(t) {
  return m({ ...t, state: !0, attribute: !1 });
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Ot = (t, e, i) => (i.configurable = !0, i.enumerable = !0, Reflect.decorate && typeof e != "object" && Object.defineProperty(t, e, i), i);
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function Tt(t, e) {
  return (i, s, r) => {
    const a = (n) => {
      var c;
      return ((c = n.renderRoot) == null ? void 0 : c.querySelector(t)) ?? null;
    };
    return Ot(i, s, { get() {
      return a(this);
    } });
  };
}
class Pt {
  constructor(e) {
    this.hass = e;
  }
  send(e) {
    return this.hass().connection.sendMessagePromise(e);
  }
  config() {
    return this.send({ type: "geekmagic/config" });
  }
  async views() {
    return (await this.send({ type: "geekmagic/views/list" })).views;
  }
  async devices() {
    return (await this.send({ type: "geekmagic/devices/list" })).devices;
  }
  async createView(e) {
    return (await this.send({
      type: "geekmagic/views/create",
      name: e,
      layout: "grid_2x2",
      theme: "watchos",
      widgets: []
    })).view;
  }
  /** Save an imported view as a new view (theme always explicit). */
  async importView(e, i) {
    return (await this.send({
      type: "geekmagic/views/create",
      name: e,
      layout: i.layout,
      theme: i.theme,
      widgets: i.widgets
    })).view;
  }
  /** Replace a stored view's layout, theme and widgets (it keeps its name and id). */
  async replaceView(e, i) {
    return (await this.send({
      type: "geekmagic/views/update",
      view_id: e,
      layout: i.layout,
      theme: i.theme,
      widgets: i.widgets
    })).view;
  }
  /** Remap a view's entity ids and validate it, saving nothing. */
  checkView(e, i = {}) {
    return this.send({ type: "geekmagic/views/check", view_config: e, entity_map: i });
  }
  updateView(e) {
    return this.send({
      type: "geekmagic/views/update",
      view_id: e.id,
      name: e.name,
      layout: e.layout,
      theme: e.theme,
      widgets: e.widgets
    });
  }
  deleteView(e) {
    return this.send({ type: "geekmagic/views/delete", view_id: e });
  }
  async duplicateView(e) {
    return (await this.send({ type: "geekmagic/views/duplicate", view_id: e })).view;
  }
  assignViews(e, i) {
    return this.send({
      type: "geekmagic/devices/assign_views",
      entry_id: e,
      view_ids: i
    });
  }
  showView(e, i) {
    return this.send({ type: "geekmagic/devices/show_view", entry_id: e, view_id: i });
  }
  render(e) {
    return this.send({
      type: "geekmagic/preview/render",
      view_config: { layout: e.layout, theme: e.theme, widgets: e.widgets }
    });
  }
  callService(e, i, s) {
    return this.hass().callService(e, i, s);
  }
}
async function be(t, e, i) {
  const s = [...t], r = Array.from({ length: Math.min(e, s.length) }, async () => {
    for (; s.length; ) await i(s.shift());
  });
  await Promise.all(r);
}
const te = (t) => `data:image/png;base64,${t}`;
class et {
  constructor(e, i, s = 250) {
    this.fetch = e, this.onChange = i, this.delay = s, this.seq = 0, this.state = { result: null, loading: !1, error: null };
  }
  /** Request a render after the debounce delay (cancels a pending one). */
  request(e) {
    clearTimeout(this.timer), this.timer = setTimeout(() => {
      this.timer = void 0, this.run(e);
    }, this.delay);
  }
  /** Render now, skipping the debounce. */
  now(e) {
    return clearTimeout(this.timer), this.timer = void 0, this.run(e);
  }
  /**
   * Re-render in the background (live data moved on): no loading state, and
   * a failure keeps the current image silently. Skipped while a render is
   * due or running, which will be at least as fresh.
   */
  async refresh(e) {
    if (this.timer !== void 0 || this.state.loading) return;
    const i = ++this.seq;
    try {
      const s = await this.fetch(e);
      i === this.seq && this.set({ result: s, error: null });
    } catch {
    }
  }
  dispose() {
    clearTimeout(this.timer), this.seq += 1;
  }
  set(e) {
    this.state = { ...this.state, ...e }, this.onChange(this.state);
  }
  async run(e) {
    const i = ++this.seq;
    this.set({ loading: !0 });
    try {
      const s = await this.fetch(e);
      if (i !== this.seq) return;
      this.set({ result: s, loading: !1, error: null });
    } catch (s) {
      if (i !== this.seq) return;
      this.set({ loading: !1, error: S(s) });
    }
  }
}
function S(t) {
  return t && typeof t == "object" && "message" in t ? String(t.message) : String(t);
}
function De(t) {
  return JSON.parse(JSON.stringify(t));
}
function F(t, e) {
  return t.widgets.find((i) => i.slot === e);
}
function ye(t, e, i) {
  const r = F(t, e) ? t.widgets.map((a) => a.slot === e ? { ...a, ...i, slot: e } : a) : [...t.widgets, { type: "", ...i, slot: e }];
  return { ...t, widgets: r };
}
function zt(t, e, i, s = {}) {
  const r = F(t, e), a = { slot: e, type: i, options: { ...s } };
  r != null && r.entity_id && (a.entity_id = r.entity_id), r != null && r.label && (a.label = r.label);
  const n = r ? t.widgets.map((c) => c.slot === e ? a : c) : [...t.widgets, a];
  return { ...t, widgets: n };
}
function Mt(t, e, i, s) {
  const r = F(t, e), a = { ...(r == null ? void 0 : r.options) ?? {} };
  return s === void 0 ? delete a[i] : a[i] = s, ye(t, e, { options: a });
}
function He(t, e, i) {
  if (e === i) return t;
  const s = t.widgets.map(
    (r) => r.slot === e ? { ...r, slot: i } : r.slot === i ? { ...r, slot: e } : r
  );
  return { ...t, widgets: s };
}
function Nt(t, e) {
  return { ...t, widgets: t.widgets.filter((i) => i.slot !== e) };
}
function Lt(t, e) {
  return t.widgets.filter((i) => i.slot >= e && i.type);
}
function Rt(t, e) {
  return { ...t, widgets: t.widgets.filter((i) => i.slot < e) };
}
function Dt(t, e) {
  return t.widgets.filter((i) => i.type && i.slot < e).length;
}
function O(t, e, i = `${e}s`) {
  return `${t} ${t === 1 ? e : i}`;
}
function $e(t, e) {
  var i;
  return ((i = t == null ? void 0 : t.layout_types[e]) == null ? void 0 : i.slots) ?? 4;
}
function Ht(t, e) {
  var a;
  const i = ((a = t == null ? void 0 : t.layout_types[e.layout]) == null ? void 0 : a.name) ?? e.layout, s = (t == null ? void 0 : t.themes[e.theme]) ?? e.theme, r = Dt(e, $e(t, e.layout));
  return `${i} · ${s} · ${O(r, "widget")}`;
}
function Ut(t, e, i) {
  return t.label ? t.label : t.entity_id ? e(t.entity_id) ?? t.entity_id : i;
}
function jt(t) {
  const e = [5, 10, 15, 30, 60, 120, 300];
  return (e.includes(t) || t <= 0 ? e : [...e, t].sort((s, r) => s - r)).map((s) => ({ value: s, label: tt(s) }));
}
function tt(t) {
  return t < 60 ? `${t} s` : t % 60 === 0 ? `${t / 60} min` : `${Math.floor(t / 60)} min ${t % 60} s`;
}
function It(t, e) {
  if (!t) return null;
  const i = t.includes("?") ? "&" : "?";
  return e ? `${t}${i}v=${encodeURIComponent(e)}` : t;
}
function it(t, e = "New view") {
  const i = new Set(t.map((r) => r.name));
  if (!i.has(e)) return e;
  let s = 2;
  for (; i.has(`${e} ${s}`); ) s += 1;
  return `${e} ${s}`;
}
const re = P`
  :host {
    --gm-radius: var(--ha-card-border-radius, 12px);
    --gm-bezel: #121212;
    --gm-gap: 16px;
    --gm-muted: var(--secondary-text-color);
    --gm-tint: rgba(var(--rgb-primary-color, 3, 169, 244), 0.12);
    font-family: var(--ha-font-family-body, Roboto, sans-serif);
  }

  * {
    box-sizing: border-box;
  }

  h1,
  h2,
  h3,
  p {
    margin: 0;
  }

  .muted {
    color: var(--gm-muted);
  }

  .section-title {
    display: flex;
    align-items: baseline;
    gap: 8px;
    font-size: 20px;
    font-weight: 400;
    line-height: 28px;
    color: var(--primary-text-color);
    margin: 0 0 12px;
  }

  .section-title .count {
    font-size: 14px;
    color: var(--gm-muted);
  }

  .icon-badge {
    --size: 40px;
    flex: none;
    width: var(--size);
    height: var(--size);
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    background: var(--badge-color, var(--primary-color));
    --mdc-icon-size: calc(var(--size) * 0.55);
  }

  .skeleton {
    background: linear-gradient(
      100deg,
      var(--secondary-background-color) 30%,
      var(--divider-color) 50%,
      var(--secondary-background-color) 70%
    );
    background-size: 300% 100%;
    animation: shimmer 1.4s ease-in-out infinite;
  }

  @keyframes shimmer {
    from {
      background-position: 100% 0;
    }
    to {
      background-position: 0 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .skeleton {
      animation: none;
    }
  }

  /* Zero specificity: component classes restyle these freely. */
  :where(button.reset) {
    font: inherit;
    color: inherit;
    background: none;
    border: 0;
    padding: 0;
    margin: 0;
    cursor: pointer;
    text-align: inherit;
  }

  :where(button.reset):focus-visible,
  .focus-ring:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .grow {
    flex: 1;
    min-width: 0;
  }

  .ellipsis {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
`, Ue = {
  values: "#0a84ff",
  home: "#30a14e",
  time: "#ff9f0a",
  history: "#8e5cf6",
  pictures: "#e0436b",
  custom: "#5f6b7a"
}, Vt = {
  values: "Values",
  home: "Home",
  time: "Time & weather",
  history: "History",
  pictures: "Pictures",
  custom: "Custom"
}, x = {
  back: "M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z",
  dots: "M12,16A2,2 0 0,1 14,18A2,2 0 0,1 12,20A2,2 0 0,1 10,18A2,2 0 0,1 12,16M12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12A2,2 0 0,1 12,10M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8A2,2 0 0,1 10,6A2,2 0 0,1 12,4Z",
  prev: "M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z",
  next: "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",
  plus: "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",
  close: "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
  up: "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z",
  down: "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z",
  delete: "M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"
};
function qt(t, e = 1500) {
  const s = 6e4 - t % 6e4 + e;
  return s > 6e4 ? s - 6e4 : s;
}
function st(t, e = 1500) {
  let i;
  const s = () => {
    i = setTimeout(() => {
      s(), t();
    }, qt(Date.now(), e));
  };
  return s(), () => clearTimeout(i);
}
const je = "Settings → Devices & services";
function rt(t) {
  const e = t.state ?? "loaded";
  return e === "loaded" ? t.online ? { kind: "online", live: !0, label: "Online" } : { kind: "offline", live: !0, label: "Offline" } : t.disabled ? {
    kind: "disabled",
    live: !1,
    label: "Disabled",
    title: "This display is disabled",
    hint: `Enable it in ${je} to show your views on it again.`,
    alert: "info"
  } : e === "setup_retry" ? {
    kind: "retrying",
    live: !1,
    label: "Not connected",
    title: `Can't reach the display at ${t.host}`,
    hint: "Home Assistant keeps retrying on its own. Check that the display is powered on and reachable on your network.",
    alert: "warning"
  } : e === "setup_in_progress" || e === "unload_in_progress" ? {
    kind: "starting",
    live: !1,
    label: "Connecting",
    title: "Connecting to the display…",
    alert: "info"
  } : {
    kind: "failed",
    live: !1,
    label: "Not loaded",
    title: "Home Assistant couldn't set up this display",
    hint: `Check the Home Assistant logs, then reload it from ${je}.`,
    alert: "error"
  };
}
function Bt(t) {
  return t.some((e) => {
    const i = rt(e).kind;
    return i === "retrying" || i === "starting";
  });
}
function ie(t, e, i) {
  const s = e + i;
  if (e < 0 || e >= t.length || s < 0 || s >= t.length)
    return t;
  const r = [...t], [a] = r.splice(e, 1);
  return r.splice(s, 0, a), r;
}
function Ft(t, e, i) {
  return ie(t, e, i - e);
}
function Gt(t, e) {
  return [...t, ...e.filter((i) => !t.includes(i))];
}
function Wt(t, e) {
  return t.filter((i) => i !== e);
}
function Ie(t, e, i) {
  if (t.length === 0) return null;
  const s = e ? t.indexOf(e) : -1;
  return s < 0 ? t[i === 1 ? 0 : t.length - 1] : t[(s + i + t.length) % t.length];
}
function Ee(t, e) {
  if (t.value !== void 0 && t.value !== null)
    return t.value;
  if (t.index !== void 0 && t.index !== null)
    return e[t.index];
}
var Zt = Object.defineProperty, Jt = Object.getOwnPropertyDescriptor, ae = (t, e, i, s) => {
  for (var r = s > 1 ? void 0 : s ? Jt(e, i) : e, a = t.length - 1, n; a >= 0; a--)
    (n = t[a]) && (r = (s ? n(e, i, r) : n(r)) || r);
  return s && r && Zt(e, i, r), r;
};
let j = class extends E {
  constructor() {
    super(...arguments), this.heading = "", this.open = !1, this.wide = !1;
  }
  updated(t) {
    t.has("open") && (this.open && !this._dialog.open && this._dialog.showModal(), !this.open && this._dialog.open && this._dialog.close());
  }
  _cancel(t) {
    t.preventDefault(), this.dispatchEvent(new CustomEvent("cancel"));
  }
  _backdrop(t) {
    t.target === this._dialog && this._cancel(t);
  }
  render() {
    return o`
      <dialog
        aria-labelledby="heading"
        @cancel=${this._cancel}
        @click=${this._backdrop}
      >
        <div class="surface">
          <h2 id="heading">${this.heading}</h2>
          <div class="body"><slot></slot></div>
          <div class="actions"><slot name="actions"></slot></div>
        </div>
      </dialog>
    `;
  }
};
j.styles = P`
    dialog {
      padding: 0;
      border: 0;
      border-radius: 28px;
      background: var(--ha-dialog-surface-background, var(--card-background-color));
      color: var(--primary-text-color);
      width: min(440px, calc(100vw - 32px));
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
    }
    :host([wide]) dialog {
      width: min(820px, calc(100vw - 32px));
    }
    dialog::backdrop {
      background: rgba(0, 0, 0, 0.45);
    }
    .surface {
      padding: 24px;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 22px;
      font-weight: 400;
      line-height: 28px;
    }
    .body {
      color: var(--secondary-text-color);
      font-size: 14px;
      line-height: 20px;
    }
    .actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 24px;
    }
  `;
ae([
  m()
], j.prototype, "heading", 2);
ae([
  m({ type: Boolean, reflect: !0 })
], j.prototype, "open", 2);
ae([
  m({ type: Boolean, reflect: !0 })
], j.prototype, "wide", 2);
ae([
  Tt("dialog")
], j.prototype, "_dialog", 2);
j = ae([
  N("gm-dialog")
], j);
const Kt = 8;
function Yt(t, e, i, s = Kt) {
  const r = Math.max(s, i.width - t.right), a = Math.max(0, i.height - t.bottom - s), n = Math.max(0, t.top - s);
  return e <= a || a >= n ? { top: t.bottom, right: r, maxHeight: a } : { bottom: i.height - t.top, right: r, maxHeight: n };
}
var Qt = Object.defineProperty, Xt = Object.getOwnPropertyDescriptor, ne = (t, e, i, s) => {
  for (var r = s > 1 ? void 0 : s ? Xt(e, i) : e, a = t.length - 1, n; a >= 0; a--)
    (n = t[a]) && (r = (s ? n(e, i, r) : n(r)) || r);
  return s && r && Qt(e, i, r), r;
};
let I = class extends E {
  constructor() {
    super(...arguments), this.items = [], this.label = "More actions", this._open = !1, this._at = { top: 0, right: 0, maxHeight: 0 }, this._outside = (t) => {
      t.composedPath().includes(this) || (this._open = !1);
    }, this._keys = (t) => {
      t.key === "Escape" && (this._open = !1);
    }, this._close = () => {
      this._open = !1;
    }, this._scrollAway = (t) => {
      this._open && !t.composedPath().some((e) => e instanceof HTMLElement && e.classList.contains("menu")) && (this._open = !1);
    };
  }
  connectedCallback() {
    super.connectedCallback(), document.addEventListener("click", this._outside, !0), document.addEventListener("keydown", this._keys), window.addEventListener("resize", this._close), document.addEventListener("wheel", this._scrollAway, { passive: !0, capture: !0 }), document.addEventListener("touchmove", this._scrollAway, { passive: !0, capture: !0 });
  }
  disconnectedCallback() {
    document.removeEventListener("click", this._outside, !0), document.removeEventListener("keydown", this._keys), window.removeEventListener("resize", this._close), document.removeEventListener("wheel", this._scrollAway, !0), document.removeEventListener("touchmove", this._scrollAway, !0), super.disconnectedCallback();
  }
  updated(t) {
    var e;
    if (t.has("_open") && this._open) {
      const i = this.renderRoot.querySelector(".menu");
      if (i) {
        const s = { width: window.innerWidth, height: window.innerHeight };
        this._at = Yt(this.getBoundingClientRect(), i.scrollHeight, s);
      }
      (e = this.renderRoot.querySelector("[role=menuitem]:not([disabled])")) == null || e.focus();
    }
  }
  _toggle(t) {
    t.stopPropagation(), this._open = !this._open;
  }
  _menuStyle() {
    const { top: t, bottom: e, right: i, maxHeight: s } = this._at;
    return `${e === void 0 ? `top:${t}px` : `bottom:${e}px`};right:${i}px;max-height:${s}px`;
  }
  _pick(t, e) {
    t.stopPropagation(), !e.disabled && (this._open = !1, this.dispatchEvent(new CustomEvent("action", { detail: e.key })));
  }
  render() {
    return o`
      <ha-icon-button
        .path=${x.dots}
        .label=${this.label}
        aria-haspopup="menu"
        aria-expanded=${this._open ? "true" : "false"}
        @click=${this._toggle}
      ></ha-icon-button>
      ${this._open ? o`<div
            class="menu"
            role="menu"
            style=${this._menuStyle()}
            @click=${(t) => t.stopPropagation()}
          >
            ${this.items.map(
      (t) => o`<button
                role="menuitem"
                class=${t.danger ? "danger" : ""}
                ?disabled=${t.disabled}
                @click=${(e) => this._pick(e, t)}
              >
                ${t.icon ? o`<ha-icon .icon=${t.icon}></ha-icon>` : d}
                <span>${t.label}</span>
              </button>`
    )}
          </div>` : d}
    `;
  }
};
I.styles = P`
    :host {
      position: relative;
      display: inline-block;
    }
    .menu {
      position: fixed;
      z-index: 10;
      overflow: auto;
      min-width: 200px;
      padding: 4px 0;
      border-radius: 12px;
      background: var(--card-background-color);
      box-shadow: 0 6px 24px rgba(0, 0, 0, 0.22);
      border: 1px solid var(--divider-color);
    }
    button {
      display: flex;
      align-items: center;
      gap: 12px;
      width: 100%;
      padding: 10px 16px;
      font: inherit;
      font-size: 14px;
      text-align: left;
      color: var(--primary-text-color);
      background: none;
      border: 0;
      cursor: pointer;
      --mdc-icon-size: 20px;
    }
    button:hover:not([disabled]),
    button:focus-visible {
      background: var(--secondary-background-color);
      outline: none;
    }
    button[disabled] {
      color: var(--disabled-text-color);
      cursor: default;
    }
    button.danger {
      color: var(--error-color);
    }
    ha-icon {
      color: var(--secondary-text-color);
    }
    button.danger ha-icon {
      color: inherit;
    }
  `;
ne([
  m({ attribute: !1 })
], I.prototype, "items", 2);
ne([
  m()
], I.prototype, "label", 2);
ne([
  u()
], I.prototype, "_open", 2);
ne([
  u()
], I.prototype, "_at", 2);
I = ne([
  N("gm-menu")
], I);
var ei = Object.defineProperty, ti = Object.getOwnPropertyDescriptor, q = (t, e, i, s) => {
  for (var r = s > 1 ? void 0 : s ? ti(e, i) : e, a = t.length - 1, n; a >= 0; a--)
    (n = t[a]) && (r = (s ? n(e, i, r) : n(r)) || r);
  return s && r && ei(e, i, r), r;
};
let T = class extends E {
  constructor() {
    super(...arguments), this.src = null, this.alt = "", this.size = 240, this.imgClass = "", this.busy = !1, this.dim = !1;
  }
  render() {
    const t = this.size >= 480;
    return o`
      <div class="bezel" style="--size: ${this.size}px">
        <div class="screen">
          ${this.src ? o`<img
                class=${this.imgClass}
                src=${this.src}
                alt=${this.alt}
                draggable="false"
                style=${t ? "image-rendering: pixelated" : ""}
              />` : o`<div class="empty"><slot name="empty"></slot></div>`}
          <div class="overlay"><slot></slot></div>
          ${this.busy ? o`<div class="progress"></div>` : d}
        </div>
      </div>
    `;
  }
};
T.styles = P`
    :host {
      display: inline-block;
    }
    .bezel {
      --pad: max(6px, calc(var(--size) * 0.045));
      padding: var(--pad);
      border-radius: calc(var(--pad) * 1.15);
      background: var(--gm-bezel, #121212);
      box-shadow:
        0 0 0 1px var(--divider-color),
        0 1px 2px rgba(0, 0, 0, 0.2),
        0 8px 24px rgba(0, 0, 0, 0.12);
    }
    .screen {
      position: relative;
      width: var(--size);
      height: var(--size);
      overflow: hidden;
      border-radius: 2px;
      background: #000;
    }
    img {
      display: block;
      width: 100%;
      height: 100%;
      transition: opacity 0.2s;
    }
    :host([dim]) img {
      opacity: 0.45;
    }
    .empty {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 12px;
      text-align: center;
      color: rgba(255, 255, 255, 0.7);
      font-size: 13px;
    }
    .overlay {
      position: absolute;
      inset: 0;
    }
    .progress {
      position: absolute;
      left: 0;
      right: 0;
      top: 0;
      height: 3px;
      background: linear-gradient(90deg, transparent, var(--primary-color), transparent);
      background-size: 50% 100%;
      background-repeat: no-repeat;
      animation: sweep 1s linear infinite;
      animation-delay: 0.4s;
      opacity: 0;
      animation-fill-mode: both;
    }
    @keyframes sweep {
      from {
        background-position: -50% 0;
        opacity: 1;
      }
      to {
        background-position: 150% 0;
        opacity: 1;
      }
    }
  `;
q([
  m()
], T.prototype, "src", 2);
q([
  m()
], T.prototype, "alt", 2);
q([
  m({ type: Number })
], T.prototype, "size", 2);
q([
  m({ attribute: "img-class" })
], T.prototype, "imgClass", 2);
q([
  m({ type: Boolean, reflect: !0 })
], T.prototype, "busy", 2);
q([
  m({ type: Boolean, reflect: !0 })
], T.prototype, "dim", 2);
T = q([
  N("gm-screen")
], T);
var ii = Object.defineProperty, si = Object.getOwnPropertyDescriptor, C = (t, e, i, s) => {
  for (var r = s > 1 ? void 0 : s ? si(e, i) : e, a = t.length - 1, n; a >= 0; a--)
    (n = t[a]) && (r = (s ? n(e, i, r) : n(r)) || r);
  return s && r && ii(e, i, r), r;
};
let A = class extends E {
  constructor() {
    super(...arguments), this.views = [], this.thumbs = /* @__PURE__ */ new Map(), this.narrow = !1, this._rotation = [], this._addOpen = !1, this._adding = /* @__PURE__ */ new Set(), this._brightness = null;
  }
  willUpdate(t) {
    t.has("device") && (this._rotation = [...this.device.assigned_views]);
  }
  // ---- entity helpers --------------------------------------------------------
  _state(t) {
    var i;
    const e = (i = this.device.entities) == null ? void 0 : i[t];
    return e ? this.hass.states[e] : void 0;
  }
  _notify(t) {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message: t }, bubbles: !0, composed: !0 })
    );
  }
  _changed() {
    this.dispatchEvent(new CustomEvent("devices-changed", { bubbles: !0, composed: !0 }));
  }
  async _service(t, e, i, s) {
    try {
      await this.api.callService(t, e, i);
    } catch (r) {
      this._notify(`Couldn't ${s}: ${S(r)}`);
    }
    this._changed();
  }
  // ---- actions -------------------------------------------------------------------
  async _show(t) {
    if (t) {
      try {
        await this.api.showView(this.device.entry_id, t);
      } catch (e) {
        this._notify(`Couldn't show that view: ${S(e)}`);
      }
      this._changed();
    }
  }
  async _setRotation(t, e) {
    const i = this._rotation;
    this._rotation = t;
    try {
      await this.api.assignViews(this.device.entry_id, t);
    } catch (s) {
      this._rotation = i, this._notify(`Couldn't ${e}: ${S(s)}`);
    }
    this._changed();
  }
  _thumbAction(t, e, i) {
    switch (i) {
      case "show":
        this._show(t);
        break;
      case "edit":
        this.dispatchEvent(new CustomEvent("edit-view", { detail: t, bubbles: !0, composed: !0 }));
        break;
      case "earlier":
        this._setRotation(ie(this._rotation, e, -1), "reorder the rotation");
        break;
      case "later":
        this._setRotation(ie(this._rotation, e, 1), "reorder the rotation");
        break;
      case "remove":
        this._setRotation(Wt(this._rotation, t), "remove the view");
        break;
    }
  }
  // ---- render --------------------------------------------------------------------
  render() {
    const t = this.device, e = rt(t), i = this._state("preview"), s = this._state("active"), r = (s == null ? void 0 : s.state) === "off", a = t.display_mode === "builtin", n = i && i.state !== "unavailable" ? It(i.attributes.entity_picture, i.state) : null, c = n && this.hass.hassUrl ? this.hass.hassUrl(n) : n, l = this.views.find((h) => h.id === t.current_view_id);
    return o`
      <ha-card outlined>
        <div class="top ${this.narrow ? "narrow" : ""}">
          <gm-screen
            .src=${c}
            .size=${this.narrow ? 200 : 184}
            alt="${t.name}'s screen"
            ?dim=${!t.online || r}
          >
            <div slot="empty" class="screen-empty">
              ${t.online ? o`<ha-spinner size="s"></ha-spinner><span>Waiting for the first frame</span>` : o`<ha-icon icon=${e.kind === "disabled" ? "mdi:monitor-off" : "mdi:lan-disconnect"}></ha-icon
                    ><span>${e.label}</span>`}
            </div>
            ${r ? o`<div class="screen-badge"><ha-icon icon="mdi:pause"></ha-icon></div>` : d}
          </gm-screen>
          <div class="info">
            <div class="name-row">
              <h2 class="ellipsis">${t.name}</h2>
              <span class="status ${e.kind}">
                <span class="led"></span>${e.label}
              </span>
            </div>
            <a class="host" href="http://${t.host}" target="_blank" rel="noopener noreferrer">${t.host}</a>

            ${e.live ? t.online ? r ? o`<div class="now">
                    <span class="now-label">Paused</span>
                    <ha-button size="s" appearance="filled" @click=${() => this._service("switch", "turn_on", { entity_id: s.entity_id }, "resume")}>Resume</ha-button>
                  </div>` : a ? o`<div class="now">
                      <ha-icon icon="mdi:television-classic"></ha-icon>
                      <span class="now-label">Built-in: <strong>${t.builtin_mode ?? "firmware screen"}</strong></span>
                      ${this._rotation.length ? o`<ha-button size="s" appearance="filled" @click=${() => this._show(this._rotation[0])}>Show my views</ha-button>` : d}
                    </div>` : o`<div class="now">
                      <span class="now-label">Now showing</span>
                      <strong class="ellipsis now-view">${(l == null ? void 0 : l.name) ?? (this._rotation.length ? "—" : "Welcome screen")}</strong>
                      ${this._rotation.length > 1 ? o`<span class="stepper">
                            <ha-icon-button .path=${x.prev} label="Previous view" @click=${() => this._show(Ie(this._rotation, t.current_view_id ?? null, -1))}></ha-icon-button>
                            <ha-icon-button .path=${x.next} label="Next view" @click=${() => this._show(Ie(this._rotation, t.current_view_id ?? null, 1))}></ha-icon-button>
                          </span>` : d}
                    </div>` : o`<ha-alert alert-type="warning">Can't reach the display at ${t.host}.</ha-alert>` : this._renderNotLoaded(e)}
            ${e.live ? this._renderControls(!t.online) : d}
          </div>
        </div>
        ${this._renderRotation(e.live)}
      </ha-card>
      ${this._addOpen ? this._renderAddDialog() : d}
    `;
  }
  _renderNotLoaded(t) {
    const e = this.device.reason;
    return o`<ha-alert class="not-loaded" alert-type=${t.alert ?? "warning"} title=${t.title ?? ""}>
      ${e ? o`<div class="reason">${e}</div>` : d}
      ${t.hint ? o`<div>${t.hint}</div>` : d}
    </ha-alert>`;
  }
  _renderControls(t) {
    const e = this._state("brightness"), i = this._state("view_cycling"), s = this._state("cycle_interval"), r = this._brightness ?? Number((e == null ? void 0 : e.state) ?? NaN), a = Number((s == null ? void 0 : s.state) ?? NaN), n = jt(Number.isFinite(a) ? a : 30);
    return o`<div class="controls">
      ${e && Number.isFinite(r) ? o`<div class="control">
            <ha-icon icon="mdi:brightness-6" title="Brightness"></ha-icon>
            <ha-slider
              class="grow"
              min="0"
              max="100"
              step="1"
              .value=${r}
              ?disabled=${t}
              aria-label="Brightness"
              @input=${(c) => this._brightness = Number(c.target.value)}
              @change=${async (c) => {
      const l = Number(c.target.value);
      await this._service("number", "set_value", { entity_id: e.entity_id, value: l }, "set the brightness"), this._brightness = null;
    }}
            ></ha-slider>
            <span class="value">${Math.round(r)}%</span>
          </div>` : d}
      ${i && this._rotation.length > 1 ? o`<div class="control">
            <ha-icon icon="mdi:rotate-right" title="Rotate views"></ha-icon>
            <label class="grow switch-label" for="cycle-${this.device.entry_id}">Rotate views</label>
            ${i.state === "on" && s && Number.isFinite(a) ? o`<ha-select
                  class="interval"
                  label="Every"
                  .value=${String(a)}
                  .options=${n.map((c) => ({ value: String(c.value), label: c.label }))}
                  ?disabled=${t}
                  @selected=${(c) => {
      const l = Ee(c.detail, n.map((h) => String(h.value)));
      l && Number(l) !== a && this._service("number", "set_value", { entity_id: s.entity_id, value: Number(l) }, "change the interval");
    }}
                  @closed=${(c) => c.stopPropagation()}
                >
                  ${n.map((c) => o`<mwc-list-item value=${String(c.value)}>${c.label}</mwc-list-item>`)}
                </ha-select>` : d}
            <ha-switch
              id="cycle-${this.device.entry_id}"
              .checked=${i.state === "on"}
              ?disabled=${t}
              @change=${(c) => this._service("switch", c.target.checked ? "turn_on" : "turn_off", { entity_id: i.entity_id }, "change rotation")}
            ></ha-switch>
          </div>` : d}
    </div>`;
  }
  /** ``live``: the display runs, so a view can be shown now. */
  _renderRotation(t) {
    var n, c;
    const e = new Map(this.views.map((l) => [l.id, l])), i = this._rotation.filter((l) => e.has(l)), s = ((n = this._state("view_cycling")) == null ? void 0 : n.state) === "on", r = this.views.filter((l) => !this._rotation.includes(l.id)), a = this.device.display_mode === "builtin" ? null : this.device.current_view_id;
    return o`<div class="rotation">
      <div class="rotation-head">
        <span class="caption">Rotation</span>
        <span class="muted">${O(i.length, "view")}</span>
        ${t ? i.length > 1 && !s ? o`<span class="muted hint">Rotation is off: tap a view to show it.</span>` : i.length > 1 ? o`<span class="muted hint">Every ${tt(Number(((c = this._state("cycle_interval")) == null ? void 0 : c.state) ?? 0))}</span>` : d : o`<span class="muted hint">Changes apply once the display is back.</span>`}
      </div>
      <div class="strip-row">
        <ha-sortable
          draggable-selector=".thumb"
          .disabled=${this.narrow}
          @item-moved=${(l) => {
      l.stopPropagation(), this._setRotation(Ft(i, l.detail.oldIndex, l.detail.newIndex), "reorder the rotation");
    }}
        >
          <div class="strip" role="list">
            ${i.map((l, h) => {
      const p = e.get(l), g = l === a;
      return o`<div class="thumb ${g ? "current" : ""}" role="listitem" data-view-id=${l}>
                <button
                  class="reset thumb-button focus-ring"
                  aria-current=${g ? "true" : "false"}
                  aria-label=${t ? `Show ${p.name} now` : p.name}
                  title=${g ? `${p.name} (on screen)` : t ? `Show ${p.name} now` : p.name}
                  aria-disabled=${t ? "false" : "true"}
                  @click=${() => t && this._show(l)}
                >
                  ${this.thumbs.get(l) ? o`<img src=${this.thumbs.get(l)} alt="" draggable="false" />` : o`<span class="skeleton"></span>`}
                  <span class="thumb-name ellipsis">${p.name}</span>
                </button>
                <gm-menu
                  class="thumb-menu"
                  label="${p.name} actions"
                  .items=${[
        { key: "show", label: "Show now", icon: "mdi:monitor-eye", disabled: g || !t },
        { key: "edit", label: "Edit view", icon: "mdi:pencil" },
        { key: "earlier", label: "Move earlier", icon: "mdi:arrow-left", disabled: h === 0 },
        { key: "later", label: "Move later", icon: "mdi:arrow-right", disabled: h === i.length - 1 },
        { key: "remove", label: "Remove from rotation", icon: "mdi:playlist-remove", danger: !0 }
      ]}
                  @action=${(f) => this._thumbAction(l, this._rotation.indexOf(l), f.detail)}
                ></gm-menu>
              </div>`;
    })}
          </div>
        </ha-sortable>
        ${r.length || !i.length ? o`<button
              class="reset add-thumb focus-ring ${i.length ? "" : "wide"}"
              @click=${() => {
      this._adding = /* @__PURE__ */ new Set(), this._addOpen = !0;
    }}
              ?disabled=${!r.length}
            >
              <ha-svg-icon .path=${x.plus}></ha-svg-icon>
              <span>${i.length ? "Add" : "Add views to show on this display"}</span>
              ${i.length ? d : o`<span class="muted">Until then it shows the welcome screen.</span>`}
            </button>` : d}
      </div>
    </div>`;
  }
  _renderAddDialog() {
    const t = this.views.filter((i) => !this._rotation.includes(i.id)), e = (i) => {
      const s = new Set(this._adding);
      s.has(i) ? s.delete(i) : s.add(i), this._adding = s;
    };
    return o`<gm-dialog open heading="Add to ${this.device.name}" @cancel=${() => this._addOpen = !1}>
      <div class="pick-grid">
        ${t.map(
      (i) => o`<label class="pick ${this._adding.has(i.id) ? "on" : ""}">
            <input type="checkbox" .checked=${this._adding.has(i.id)} @change=${() => e(i.id)} />
            ${this.thumbs.get(i.id) ? o`<img src=${this.thumbs.get(i.id)} alt="" />` : o`<span class="skeleton"></span>`}
            <span class="ellipsis">${i.name}</span>
          </label>`
    )}
      </div>
      <ha-button slot="actions" appearance="plain" @click=${() => this._addOpen = !1}>Cancel</ha-button>
      <ha-button
        slot="actions"
        variant="brand"
        appearance="accent"
        ?disabled=${!this._adding.size}
        @click=${() => {
      this._addOpen = !1;
      const i = t.filter((s) => this._adding.has(s.id)).map((s) => s.id);
      this._setRotation(Gt(this._rotation, i), "add the views");
    }}
        >Add ${this._adding.size ? O(this._adding.size, "view") : ""}</ha-button
      >
    </gm-dialog>`;
  }
};
A.styles = [
  re,
  P`
      :host {
        display: block;
        min-width: 0;
      }
      ha-card {
        overflow: hidden;
      }
      .top {
        display: flex;
        gap: 24px;
        padding: 20px;
        align-items: flex-start;
      }
      .top.narrow {
        flex-direction: column;
        align-items: center;
        padding: 16px;
        gap: 16px;
      }
      .info {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 10px;
        width: 100%;
      }
      .name-row {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      h2 {
        font-size: 22px;
        font-weight: 400;
        line-height: 28px;
        min-width: 0;
      }
      .status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: var(--secondary-text-color);
        white-space: nowrap;
      }
      .led {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--disabled-text-color);
      }
      .online .led {
        background: var(--success-color, #43a047);
        box-shadow: 0 0 0 3px rgba(67, 160, 71, 0.18);
      }
      .retrying .led,
      .starting .led {
        background: var(--warning-color, #ffa600);
      }
      .failed .led {
        background: var(--error-color, #db4437);
      }
      .not-loaded .reason {
        margin-bottom: 4px;
        font-size: 12px;
        line-height: 16px;
        overflow-wrap: anywhere;
        color: var(--secondary-text-color);
      }
      .host {
        margin-top: -8px;
        font-size: 13px;
        color: var(--secondary-text-color);
        text-decoration: none;
        width: fit-content;
      }
      .host:hover {
        text-decoration: underline;
      }
      .now {
        display: flex;
        align-items: center;
        gap: 8px;
        min-height: 48px;
        padding: 4px 4px 4px 14px;
        border-radius: 12px;
        background: var(--secondary-background-color);
        font-size: 14px;
      }
      .now-label {
        color: var(--secondary-text-color);
        white-space: nowrap;
      }
      .now-view {
        flex: 1;
        min-width: 0;
        font-weight: 500;
      }
      .now > ha-button {
        margin-left: auto;
      }
      .stepper {
        display: flex;
        margin-left: auto;
      }
      .controls {
        display: flex;
        flex-direction: column;
      }
      .control {
        display: flex;
        align-items: center;
        gap: 12px;
        min-height: 52px;
        padding-left: 14px;
        color: var(--secondary-text-color);
      }
      .control + .control {
        border-top: 1px solid var(--divider-color);
      }
      .control ha-icon {
        flex: none;
      }
      .value {
        width: 44px;
        text-align: right;
        font-variant-numeric: tabular-nums;
        color: var(--primary-text-color);
        font-size: 14px;
      }
      .switch-label {
        color: var(--primary-text-color);
        font-size: 14px;
        cursor: pointer;
      }
      .interval {
        width: 120px;
      }
      .screen-empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
      }
      .screen-badge {
        position: absolute;
        right: 8px;
        bottom: 8px;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(0, 0, 0, 0.7);
        color: #fff;
      }
      .rotation {
        border-top: 1px solid var(--divider-color);
        padding: 14px 20px 18px;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .rotation-head {
        display: flex;
        align-items: baseline;
        column-gap: 12px;
        row-gap: 2px;
        flex-wrap: wrap;
        font-size: 13px;
      }
      .caption {
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--secondary-text-color);
      }
      .strip-row {
        display: flex;
        gap: 12px;
        overflow-x: auto;
        padding: 4px 2px 6px;
        scrollbar-width: thin;
      }
      ha-sortable {
        display: contents;
      }
      .strip {
        display: flex;
        gap: 12px;
      }
      .thumb {
        position: relative;
        flex: none;
        width: 92px;
      }
      .thumb-button {
        display: flex;
        flex-direction: column;
        gap: 6px;
        width: 100%;
        border-radius: 10px;
      }
      .thumb img,
      .thumb .skeleton {
        display: block;
        width: 92px;
        height: 92px;
        border-radius: 10px;
        background-color: #000;
        box-shadow: 0 0 0 1px var(--divider-color);
        transition: box-shadow 0.15s, transform 0.15s;
      }
      .thumb-button:hover:not([aria-disabled="true"]) img {
        transform: translateY(-2px);
      }
      /* Not "disabled": a disabled button swallows the pointer events the
         sortable needs, and the rotation stays reorderable. */
      .thumb-button[aria-disabled="true"] {
        cursor: default;
      }
      .thumb.current img {
        box-shadow:
          0 0 0 2px var(--card-background-color),
          0 0 0 4px var(--primary-color);
      }
      .thumb-name {
        display: block;
        font-size: 12px;
        line-height: 16px;
        color: var(--secondary-text-color);
        text-align: center;
      }
      .thumb.current .thumb-name {
        color: var(--primary-color);
        font-weight: 500;
      }
      .thumb-menu {
        position: absolute;
        top: 4px;
        right: 4px;
        border-radius: 50%;
        background: rgba(0, 0, 0, 0.6);
        --mdc-icon-button-size: 32px;
        --mdc-icon-size: 18px;
        color: #fff;
        opacity: 0;
        transition: opacity 0.12s;
      }
      .thumb:hover .thumb-menu,
      .thumb:focus-within .thumb-menu,
      .narrow ~ .rotation .thumb-menu {
        opacity: 1;
      }
      @media (hover: none) {
        .thumb-menu {
          opacity: 1;
        }
      }
      .add-thumb {
        flex: none;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 4px;
        width: 92px;
        height: 92px;
        border-radius: 10px;
        border: 2px dashed var(--divider-color);
        color: var(--secondary-text-color);
        font-size: 13px;
        --mdc-icon-size: 24px;
      }
      .add-thumb:hover {
        border-color: var(--primary-color);
        color: var(--primary-color);
      }
      .add-thumb.wide {
        width: 100%;
        height: auto;
        padding: 20px;
        text-align: center;
      }
      .add-thumb[disabled] {
        opacity: 0.5;
        cursor: default;
      }
      .pick-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
        gap: 12px;
        max-height: 50vh;
        overflow: auto;
        padding: 4px;
      }
      .pick {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: 6px;
        font-size: 12px;
        color: var(--primary-text-color);
        cursor: pointer;
      }
      .pick img,
      .pick .skeleton {
        width: 100%;
        aspect-ratio: 1;
        border-radius: 10px;
        background-color: #000;
        box-shadow: 0 0 0 1px var(--divider-color);
      }
      .pick.on img,
      .pick.on .skeleton {
        box-shadow: 0 0 0 3px var(--primary-color);
      }
      .pick input {
        position: absolute;
        top: 6px;
        left: 6px;
        width: 18px;
        height: 18px;
        accent-color: var(--primary-color);
      }
    `
];
C([
  m({ attribute: !1 })
], A.prototype, "hass", 2);
C([
  m({ attribute: !1 })
], A.prototype, "api", 2);
C([
  m({ attribute: !1 })
], A.prototype, "device", 2);
C([
  m({ attribute: !1 })
], A.prototype, "views", 2);
C([
  m({ attribute: !1 })
], A.prototype, "thumbs", 2);
C([
  m({ type: Boolean })
], A.prototype, "narrow", 2);
C([
  u()
], A.prototype, "_rotation", 2);
C([
  u()
], A.prototype, "_addOpen", 2);
C([
  u()
], A.prototype, "_adding", 2);
C([
  u()
], A.prototype, "_brightness", 2);
A = C([
  N("gm-device-card")
], A);
const ri = {
  "1x1": [
    224,
    216
  ],
  "1x2": [
    108,
    224
  ],
  "2x1": [
    224,
    108
  ],
  "2x2": [
    108,
    108
  ],
  "2x3": [
    69,
    108
  ],
  "3x2": [
    108,
    69
  ],
  "3x3": [
    72,
    72
  ]
}, ai = {
  attribute_list: "attribute_list",
  camera: "camera",
  candlestick: "candlestick",
  chart: "chart",
  climate: "climate",
  clock: "clock",
  datetime: "datetime",
  entity: "entity_icon",
  gauge: "gauge_bar",
  image: "image",
  media: "media",
  multi_progress: "multi_progress",
  progress: "progress",
  status: "status",
  status_list: "status_list",
  text: "text",
  weather: "weather"
}, at = {
  sizes: ri,
  samples: ai
}, nt = at.sizes, ni = at.samples;
function Ve(t, e) {
  return [t < 100, e < 100, Math.min(t, e) < 130];
}
function ot(t, e) {
  const i = Ve(t, e);
  let s = "", r = 1 / 0;
  for (const [a, [n, c]] of Object.entries(nt)) {
    const h = Ve(n, c).filter((p, g) => p !== i[g]).length * 10 + Math.abs(Math.log(t / n)) + Math.abs(Math.log(e / c));
    h < r && (s = a, r = h);
  }
  return s;
}
function oi(t, e, i, s, r) {
  const a = ni[i];
  return !a || !(s > 0) || !(r > 0) ? null : `${t}/${a}_${ot(s, r)}.png?v=${encodeURIComponent(e)}`;
}
function li(t) {
  return nt[t];
}
function ci(t) {
  if (!t || t.length !== 3) return "#000000";
  const [e, i, s] = t;
  return `#${[e, i, s].map((r) => Math.max(0, Math.min(255, r)).toString(16).padStart(2, "0")).join("")}`;
}
function qe(t) {
  const e = t.trim();
  if (!e) return null;
  const i = e.match(/^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/);
  if (i) {
    let a = i[1];
    return a.length === 3 && (a = a[0] + a[0] + a[1] + a[1] + a[2] + a[2]), [
      parseInt(a.slice(0, 2), 16),
      parseInt(a.slice(2, 4), 16),
      parseInt(a.slice(4, 6), 16)
    ];
  }
  const s = e.match(/^(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})$/);
  if (s) {
    const a = Math.min(255, parseInt(s[1], 10)), n = Math.min(255, parseInt(s[2], 10)), c = Math.min(255, parseInt(s[3], 10));
    return [a, n, c];
  }
  const r = e.match(
    /^rgb\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/i
  );
  if (r) {
    const a = Math.min(255, parseInt(r[1], 10)), n = Math.min(255, parseInt(r[2], 10)), c = Math.min(255, parseInt(r[3], 10));
    return [a, n, c];
  }
  return null;
}
const hi = () => ({ value: 0, color: [255, 255, 0] }), di = () => ({ entity_id: "", target: 100 }), pi = () => ({ entity_id: "" });
function ui(t, e, i) {
  const s = t.visible_when;
  return s ? Object.entries(s).every(([r, a]) => {
    const n = e.find((l) => l.key === r);
    if (!n) return !0;
    const c = (i == null ? void 0 : i[r]) ?? n.default;
    return a.some((l) => l === c);
  }) : !0;
}
function gi(t, e) {
  return t.filter((i) => ui(i, t, e));
}
var mi = Object.defineProperty, vi = Object.getOwnPropertyDescriptor, oe = (t, e, i, s) => {
  for (var r = s > 1 ? void 0 : s ? vi(e, i) : e, a = t.length - 1, n; a >= 0; a--)
    (n = t[a]) && (r = (s ? n(e, i, r) : n(r)) || r);
  return s && r && mi(e, i, r), r;
};
const _i = (() => {
  try {
    return Intl.supportedValuesOf("timeZone");
  } catch {
    return ["UTC", "Europe/London", "Europe/Paris", "America/New_York", "Asia/Tokyo"];
  }
})(), Be = (t) => Array.isArray(t) && t.length === 3 && t.every((e) => typeof e == "number");
let V = class extends E {
  constructor() {
    super(...arguments), this._expanded = /* @__PURE__ */ new Set(), this._friendly = (t) => {
      var e;
      return (e = this.hass.states[t]) == null ? void 0 : e.attributes.friendly_name;
    };
  }
  _emit(t, e) {
    this.dispatchEvent(new CustomEvent("option-change", { detail: { key: t, value: e } }));
  }
  render() {
    const t = gi(this.schema.options ?? [], this.widget.options), e = t.filter((s) => s.type === "boolean"), i = t.filter((s) => s.type !== "boolean");
    return o`
      ${i.map((s) => this._field(s))}
      ${e.length ? o`<div class="toggles" role="group" aria-label="Show">
            ${e.map((s) => this._toggle(s))}
          </div>` : d}
    `;
  }
  _value(t) {
    var e;
    return ((e = this.widget.options) == null ? void 0 : e[t.key]) ?? t.default;
  }
  _toggle(t) {
    const e = `opt-${t.key}`;
    return o`<label class="toggle" for=${e}>
      <span>${t.label}</span>
      <ha-switch
        id=${e}
        .checked=${!!this._value(t)}
        @change=${(i) => this._emit(t.key, i.target.checked)}
      ></ha-switch>
    </label>`;
  }
  _select(t, e, i, s) {
    const r = i.map((a) => a.value);
    return o`<ha-select
      .label=${t}
      .value=${e}
      .options=${i}
      @selected=${(a) => {
      const n = Ee(a.detail, r);
      n !== void 0 && n !== e && s(n);
    }}
      @closed=${(a) => a.stopPropagation()}
    >
      ${i.map((a) => o`<mwc-list-item value=${a.value}>${a.label}</mwc-list-item>`)}
    </ha-select>`;
  }
  _field(t) {
    const e = this._value(t);
    switch (t.type) {
      case "select": {
        const i = (t.options ?? []).map((s) => ({ value: s, label: s }));
        return o`<div class="field">
          ${this._select(t.label, String(e ?? ""), i, (s) => this._emit(t.key, s))}
        </div>`;
      }
      case "number":
        return o`<div class="field">
          <ha-input
            type="number"
            .label=${t.label}
            .value=${e != null ? String(e) : ""}
            .min=${t.min !== void 0 ? String(t.min) : ""}
            .max=${t.max !== void 0 ? String(t.max) : ""}
            @input=${(i) => {
          const s = i.target.value;
          this._emit(t.key, s === "" ? void 0 : parseFloat(s));
        }}
          ></ha-input>
        </div>`;
      case "text":
        return o`<div class="field">
          <ha-input
            .label=${t.label}
            .value=${e ?? ""}
            .placeholder=${t.placeholder ?? ""}
            @input=${(i) => this._emit(t.key, i.target.value)}
          ></ha-input>
        </div>`;
      case "textarea":
        return o`<div class="field">
          <label class="caption" for="ta-${t.key}">${t.label}</label>
          <textarea
            id="ta-${t.key}"
            .value=${e ?? ""}
            placeholder=${t.placeholder ?? ""}
            spellcheck="false"
            @input=${(i) => this._emit(t.key, i.target.value)}
          ></textarea>
        </div>`;
      case "icon":
        return o`<div class="field">
          <ha-icon-picker
            .hass=${this.hass}
            .label=${t.label}
            .value=${e ?? ""}
            @value-changed=${(i) => this._emit(t.key, i.detail.value || void 0)}
          ></ha-icon-picker>
        </div>`;
      case "entity":
        return o`<div class="field">
          <ha-selector
            .hass=${this.hass}
            .selector=${{ entity: {} }}
            .value=${e ?? ""}
            .label=${t.label}
            @value-changed=${(i) => this._emit(t.key, i.detail.value || void 0)}
          ></ha-selector>
        </div>`;
      case "color":
        return o`<div class="field">
          ${this._color(t.label, Be(e) ? e : void 0, (i) => this._emit(t.key, i), !0)}
        </div>`;
      case "timezone": {
        const i = [
          { value: "", label: "Home Assistant default" },
          ..._i.map((s) => ({ value: s, label: s }))
        ];
        return o`<div class="field">
          ${this._select(t.label, String(e ?? ""), i, (s) => this._emit(t.key, s))}
        </div>`;
      }
      case "thresholds":
        return this._thresholds(t, e ?? []);
      case "progress_items":
        return this._progressItems(t, e ?? []);
      case "status_entities":
        return this._statusEntities(t, e ?? []);
      default:
        return d;
    }
  }
  /**
   * Swatch + hex. Unset is not a colour: the device uses the theme's
   * semantic colour, so it shows hatched as "Theme default" (issue #170).
   */
  _color(t, e, i, s) {
    const r = e ? ci(e) : "", a = (n) => {
      const c = qe(n.target.value);
      c && i(c);
    };
    return o`<div class="color">
      <label class="swatch ${r ? "" : "unset"}" style=${r ? `background:${r}` : ""} title="Pick a colour">
        <input type="color" .value=${r || "#ffffff"} @input=${a} aria-label="${t} colour" />
      </label>
      <ha-input
        class="grow"
        .label=${t}
        .value=${r}
        placeholder="Theme default"
        @change=${(n) => {
      const c = n.target.value.trim();
      if (!c) return s ? i(void 0) : void 0;
      const l = qe(c);
      l && i(l);
    }}
      ></ha-input>
      ${s && r ? o`<ha-icon-button .path=${x.close} label="Use the theme's colour" @click=${() => i(void 0)}></ha-icon-button>` : d}
    </div>`;
  }
  _thresholds(t, e) {
    const i = (s) => this._emit(t.key, s);
    return o`<div class="array">
      <div class="array-title">${t.label}</div>
      ${e.map(
      (s, r) => o`<div class="threshold">
          <ha-input
            class="threshold-value"
            type="number"
            label="From"
            .value=${String(s.value)}
            @input=${(a) => {
        const n = [...e];
        n[r] = { ...s, value: parseFloat(a.target.value) || 0 }, i(n);
      }}
          ></ha-input>
          ${this._color("Colour", s.color, (a) => {
        const n = [...e];
        n[r] = { ...s, color: a ?? s.color }, i(n);
      }, !1)}
          <ha-icon-button .path=${x.delete} label="Remove" @click=${() => i(e.filter((a, n) => n !== r))}></ha-icon-button>
        </div>`
    )}
      <ha-button appearance="plain" size="s" @click=${() => i([...e, hi()])}>
        <ha-svg-icon slot="start" .path=${x.plus}></ha-svg-icon>Add Threshold
      </ha-button>
    </div>`;
  }
  _rows(t, e, i, s, r, a) {
    const n = (l) => this._emit(t.key, l), c = (l) => {
      const h = new Set(this._expanded);
      h.has(l) ? h.delete(l) : h.add(l), this._expanded = h;
    };
    return o`<div class="array">
      <div class="array-title">${t.label}</div>
      ${e.map((l, h) => {
      const p = `${i}-${h}`, g = this._expanded.has(p), f = (L) => {
        const le = [...e];
        le[h] = { ...l, ...L }, n(le);
      }, k = Ut(l, this._friendly, "New entity");
      return o`<div class="array-item ${g ? "open" : ""}">
          <div class="array-item-header">
            <button class="reset grow row" aria-expanded=${g ? "true" : "false"} @click=${() => c(p)}>
              ${l.entity_id ? o`<ha-state-icon .hass=${this.hass} .stateObj=${this.hass.states[l.entity_id]}></ha-state-icon>` : o`<ha-icon icon="mdi:plus-circle-outline"></ha-icon>`}
              <span class="array-item-title ellipsis grow ${l.entity_id ? "" : "muted"}">${k}</span>
            </button>
            <ha-icon-button .path=${x.up} label="Move up" .disabled=${h === 0} @click=${() => n(ie(e, h, -1))}></ha-icon-button>
            <ha-icon-button .path=${x.down} label="Move down" .disabled=${h === e.length - 1} @click=${() => n(ie(e, h, 1))}></ha-icon-button>
            <ha-icon-button .path=${x.delete} label="Remove" @click=${() => n(e.filter((L, le) => le !== h))}></ha-icon-button>
          </div>
          <div class="array-item-content ${g ? "" : "collapsed"}">${a(l, f)}</div>
        </div>`;
    })}
      <ha-button
        appearance="plain"
        size="s"
        @click=${() => {
      n([...e, r()]), this._expanded = /* @__PURE__ */ new Set([...this._expanded, `${i}-${e.length}`]);
    }}
      >
        <ha-svg-icon slot="start" .path=${x.plus}></ha-svg-icon>${s}
      </ha-button>
    </div>`;
  }
  _entity(t, e) {
    return o`<ha-selector
      .hass=${this.hass}
      .selector=${{ entity: {} }}
      .value=${t}
      .label=${"Entity"}
      @value-changed=${(i) => e(i.detail.value ?? "")}
    ></ha-selector>`;
  }
  _statusEntities(t, e) {
    return this._rows(t, e, "status", "Add Status Entity", pi, (i, s) => o`
      ${this._entity(i.entity_id, (r) => s({ entity_id: r }))}
      <ha-input label="Label" .value=${i.label ?? ""} @input=${(r) => s({ label: r.target.value })}></ha-input>
      <ha-icon-picker .hass=${this.hass} label="Icon" .value=${i.icon ?? ""} @value-changed=${(r) => s({ icon: r.detail.value || void 0 })}></ha-icon-picker>
    `);
  }
  _progressItems(t, e) {
    return this._rows(t, e, "progress", "Add Progress Item", di, (i, s) => o`
      ${this._entity(i.entity_id, (r) => s({ entity_id: r }))}
      <ha-input label="Label" .value=${i.label ?? ""} @input=${(r) => s({ label: r.target.value })}></ha-input>
      <ha-input type="number" label="Target" .value=${i.target !== void 0 ? String(i.target) : "100"} @input=${(r) => s({ target: parseFloat(r.target.value) || 100 })}></ha-input>
      <ha-icon-picker .hass=${this.hass} label="Icon" .value=${i.icon ?? ""} @value-changed=${(r) => s({ icon: r.detail.value || void 0 })}></ha-icon-picker>
      ${this._color("Colour", Be(i.color) ? i.color : void 0, (r) => s({ color: r }), !0)}
    `);
  }
};
V.styles = [
  re,
  P`
      :host {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }
      .field > * {
        display: block;
        width: 100%;
      }
      .caption {
        display: block;
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-bottom: 4px;
      }
      textarea {
        width: 100%;
        min-height: 140px;
        padding: 10px 12px;
        font-family: var(--ha-font-family-code, ui-monospace, monospace);
        font-size: 13px;
        line-height: 1.5;
        color: var(--primary-text-color);
        background: var(--secondary-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        resize: vertical;
      }
      textarea:focus {
        outline: 2px solid var(--primary-color);
        outline-offset: -1px;
      }
      .toggles {
        border: 1px solid var(--divider-color);
        border-radius: 12px;
        overflow: hidden;
      }
      .toggle {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        min-height: 48px;
        padding: 0 16px;
        cursor: pointer;
        font-size: 14px;
      }
      .toggle + .toggle {
        border-top: 1px solid var(--divider-color);
      }
      .color {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .swatch {
        position: relative;
        flex: none;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        border: 1px solid var(--divider-color);
        cursor: pointer;
      }
      .swatch.unset {
        background: repeating-linear-gradient(
          45deg,
          var(--secondary-background-color) 0 5px,
          var(--divider-color) 5px 10px
        );
      }
      .swatch input {
        position: absolute;
        inset: 0;
        opacity: 0;
        cursor: pointer;
        width: 100%;
        height: 100%;
      }
      .swatch:focus-within {
        outline: 2px solid var(--primary-color);
        outline-offset: 2px;
      }
      .array {
        display: flex;
        flex-direction: column;
        gap: 8px;
        align-items: stretch;
      }
      .array > ha-button {
        align-self: flex-start;
      }
      .array-title {
        font-size: 14px;
        font-weight: 500;
      }
      .threshold {
        display: grid;
        grid-template-columns: 96px 1fr auto;
        align-items: center;
        gap: 8px;
      }
      .array-item {
        border: 1px solid var(--divider-color);
        border-radius: 12px;
      }
      .array-item-header {
        display: flex;
        align-items: center;
        padding: 0 4px 0 12px;
        min-height: 48px;
        --mdc-icon-size: 20px;
      }
      .array-item-header > button {
        min-height: 48px;
        gap: 12px;
        color: var(--state-icon-color, var(--secondary-text-color));
      }
      .array-item-title {
        color: var(--primary-text-color);
        font-size: 14px;
      }
      .array-item-title.muted {
        color: var(--secondary-text-color);
      }
      .array-item-content {
        display: flex;
        flex-direction: column;
        gap: 12px;
        padding: 4px 12px 12px;
      }
      .array-item-content.collapsed {
        display: none;
      }
    `
];
oe([
  m({ attribute: !1 })
], V.prototype, "hass", 2);
oe([
  m({ attribute: !1 })
], V.prototype, "schema", 2);
oe([
  m({ attribute: !1 })
], V.prototype, "widget", 2);
oe([
  u()
], V.prototype, "_expanded", 2);
V = oe([
  N("gm-widget-options")
], V);
var fi = Object.defineProperty, bi = Object.getOwnPropertyDescriptor, $ = (t, e, i, s) => {
  for (var r = s > 1 ? void 0 : s ? bi(e, i) : e, a = t.length - 1, n; a >= 0; a--)
    (n = t[a]) && (r = (s ? n(e, i, r) : n(r)) || r);
  return s && r && fi(e, i, r), r;
};
const Fe = ["values", "home", "time", "history", "pictures", "custom"];
let _ = class extends E {
  constructor() {
    super(...arguments), this.previews = {
      url: "/geekmagic_previews",
      version: "dev"
    }, this._saved = "", this._slot = 0, this._tab = "widget", this._changingType = !1, this._brokenPreviews = /* @__PURE__ */ new Set(), this._saving = !1, this._discardOpen = !1, this._preview = {
      result: null,
      loading: !1,
      error: null
    }, this._themeTiles = /* @__PURE__ */ new Map(), this._width = 1200, this._dragFrom = null, this._queue = new et(
      (t) => this.api.render(t),
      (t) => this._preview = t
    ), this._resize = new ResizeObserver((t) => {
      var e;
      this._width = ((e = t[0]) == null ? void 0 : e.contentRect.width) ?? this._width;
    }), this._themeGeneration = 0;
  }
  /** True when the draft differs from what was last loaded or saved. */
  get dirty() {
    return JSON.stringify(this._draft) !== this._saved;
  }
  /** Back arrow: ask first if there are unsaved edits. */
  requestLeave() {
    this.dirty ? this._discardOpen = !0 : this._leave();
  }
  willUpdate(t) {
    var e;
    t.has("view") && this.view && this.view.id !== ((e = this._draft) == null ? void 0 : e.id) && (this._draft = De(this.view), this._saved = JSON.stringify(this._draft), this._slot = 0, this._queue.now(this._draft));
  }
  connectedCallback() {
    super.connectedCallback(), this._stopMinute = st(() => {
      document.visibilityState === "visible" && this._queue.refresh(this._draft);
    }), this.updateComplete.then(() => {
      const t = this.renderRoot.querySelector(".content");
      t && this._resize.observe(t);
    });
  }
  disconnectedCallback() {
    var t;
    (t = this._stopMinute) == null || t.call(this), this._queue.dispose(), this._resize.disconnect(), clearTimeout(this._themeTimer), this._themeGeneration += 1, super.disconnectedCallback();
  }
  // ---- edits ---------------------------------------------------------------
  get _slotCount() {
    return $e(this.config, this._draft.layout);
  }
  _edit(t, { render: e = !0 } = {}) {
    this._draft = t, e && this._queue.request(t), this._tab === "view" && this._scheduleThemeTiles();
  }
  _select(t) {
    this._slot = Math.max(0, Math.min(t, this._slotCount - 1)), this._changingType = !1, this._tab = "widget";
  }
  _pickType(t) {
    const e = t === "clock" ? { timezone: Intl.DateTimeFormat().resolvedOptions().timeZone } : {};
    this._edit(zt(this._draft, this._slot, t, e)), this._changingType = !1;
  }
  _setLayout(t) {
    const e = { ...this._draft, layout: t };
    this._edit(e), this._slot = Math.min(this._slot, $e(this.config, t) - 1);
  }
  // ---- save / leave ----------------------------------------------------------
  _notify(t) {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message: t }, bubbles: !0, composed: !0 })
    );
  }
  async _save() {
    if (this._saving) return;
    const t = this._draft;
    this._saving = !0;
    try {
      await this.api.updateView(t), this._saved = JSON.stringify(t), this._notify(`Saved "${t.name}"`), this.dispatchEvent(new CustomEvent("saved", { detail: De(t) }));
    } catch (e) {
      this._notify(`Couldn't save "${t.name}": ${S(e)}`);
    } finally {
      this._saving = !1;
    }
  }
  _leave() {
    this._discardOpen = !1, this.dispatchEvent(new CustomEvent("leave"));
  }
  // ---- theme tiles ------------------------------------------------------------
  _scheduleThemeTiles() {
    clearTimeout(this._themeTimer), this._themeTimer = setTimeout(() => void this._renderThemeTiles(), 600);
  }
  /** Render the draft in every theme (lazily, two at a time). */
  async _renderThemeTiles() {
    const t = ++this._themeGeneration, e = this._draft, i = (r) => `${r}|${e.layout}|${JSON.stringify(e.widgets)}`, s = Object.keys(this.config.themes).filter((r) => !this._themeTiles.has(i(r)));
    await be(s, 2, async (r) => {
      if (t === this._themeGeneration)
        try {
          const a = await this.api.render({ ...e, theme: r });
          if (t !== this._themeGeneration) return;
          this._themeTiles = new Map(this._themeTiles).set(i(r), te(a.image));
        } catch {
        }
    });
  }
  _themeTile(t) {
    const e = this._draft;
    return this._themeTiles.get(`${t}|${e.layout}|${JSON.stringify(e.widgets)}`);
  }
  // ---- render -----------------------------------------------------------------
  render() {
    if (!this._draft) return d;
    const t = this._width < 900;
    return o`
      <div class="toolbar editor-header">
        <ha-icon-button .path=${x.back} label="Back" @click=${() => this.requestLeave()}></ha-icon-button>
        <input
          class="title-input"
          aria-label="View name"
          .value=${this._draft.name}
          @input=${(e) => this._edit({ ...this._draft, name: e.target.value }, { render: !1 })}
        />
        ${this.dirty ? o`<span class="unsaved" title="Unsaved changes"
              ><span class="dot"></span><span class="unsaved-text">Unsaved changes</span></span
            >` : d}
        <ha-button
          variant="brand"
          appearance="accent"
          ?disabled=${!this.dirty || this._saving}
          .loading=${this._saving}
          @click=${this._save}
          >${this._saving ? "Saving…" : "Save"}</ha-button
        >
      </div>
      <div class="content ${t ? "narrow" : "wide"}">
        <div class="layout">
          <div class="stage">${this._renderStage(t)}</div>
          <div class="inspector">${this._renderInspector()}</div>
        </div>
      </div>
      ${this._discardOpen ? o`<gm-dialog open heading="Discard unsaved changes?" @cancel=${() => this._discardOpen = !1}>
            Your edits to "${this._draft.name}" haven't been saved.
            <ha-button slot="actions" appearance="plain" @click=${() => this._discardOpen = !1}>Keep editing</ha-button>
            <ha-button slot="actions" variant="danger" appearance="accent" @click=${() => this._leave()}>Discard</ha-button>
          </gm-dialog>` : d}
    `;
  }
  _screenSize(t) {
    if (t) {
      const e = Math.min(400, window.innerHeight * 0.42);
      return Math.round(Math.max(160, Math.min(this._width * 0.8, e)));
    }
    return this._width >= 1100 ? 480 : 360;
  }
  _rects() {
    var i, s;
    const t = this._slotCount, e = (i = this._preview.result) == null ? void 0 : i.slots;
    return e && e.length === t ? e.map(([r, a, n, c]) => [r / 240, a / 240, (n - r) / 240, (c - a) / 240]) : (((s = this.config.layout_types[this._draft.layout]) == null ? void 0 : s.rects) ?? []).slice(0, t);
  }
  _slotName(t) {
    const e = F(this._draft, t), i = e != null && e.type ? this.config.widget_types[e.type] : void 0, s = i ? [i.name, e == null ? void 0 : e.label].filter(Boolean).join(", ") : "Empty";
    return `Slot ${t + 1}: ${s}`;
  }
  _overlayKeys(t) {
    const e = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[t.key];
    if (e === void 0) return;
    t.preventDefault();
    const i = (this._slot + e + this._slotCount) % this._slotCount;
    this._select(i), this.updateComplete.then(
      () => {
        var s;
        return (s = this.renderRoot.querySelectorAll(".slot-hit")[i]) == null ? void 0 : s.focus();
      }
    );
  }
  _renderStage(t) {
    const e = this._screenSize(t), i = Lt(this._draft, this._slotCount), s = this._preview.result ? te(this._preview.result.image) : null, r = this._draft.widgets.every((a) => !a.type);
    return o`
      <div class="stage-inner">
        <gm-screen
          .src=${s}
          .size=${e}
          img-class="preview-image"
          alt="Preview of ${this._draft.name}"
          ?busy=${this._preview.loading}
        >
          <div class="overlay" role="listbox" aria-label="Slots" @keydown=${this._overlayKeys}>
            ${this._rects().map(([a, n, c, l], h) => {
      const p = F(this._draft, h), g = h === this._slot;
      return o`<button
                class="slot-hit ${g ? "selected" : ""} ${p != null && p.type ? "" : "empty"} ${this._dragFrom !== null && this._dragFrom !== h ? "drop" : ""}"
                style="left:${a * 100}%;top:${n * 100}%;width:${c * 100}%;height:${l * 100}%"
                role="option"
                aria-selected=${g ? "true" : "false"}
                aria-label=${this._slotName(h)}
                tabindex=${g ? 0 : -1}
                draggable=${p != null && p.type ? "true" : "false"}
                @click=${() => this._select(h)}
                @dragstart=${(f) => {
        var k;
        this._dragFrom = h, (k = f.dataTransfer) == null || k.setData("text/plain", String(h));
      }}
                @dragend=${() => this._dragFrom = null}
                @dragover=${(f) => f.preventDefault()}
                @drop=${(f) => {
        f.preventDefault(), this._dragFrom !== null && this._dragFrom !== h && (this._edit(He(this._draft, this._dragFrom, h)), this._slot = h), this._dragFrom = null;
      }}
              >
                ${p != null && p.type ? d : o`<ha-svg-icon .path=${x.plus}></ha-svg-icon>`}
              </button>`;
    })}
          </div>
          <div slot="empty" class="screen-empty">
            ${this._preview.error ? d : o`<ha-spinner size="s"></ha-spinner>`}
          </div>
        </gm-screen>
        <div class="stage-caption">
          ${r ? o`<p><strong>Pick a cell to add a widget.</strong></p>
                <p class="muted">An empty view shows a clock on the display.</p>` : o`<p class="muted">
                ${t ? "Tap" : "Click"} a cell to edit it${t ? "" : ", drag one onto another to swap"}.
              </p>`}
        </div>
        ${this._preview.error ? o`<ha-alert alert-type="error" title="Preview failed">
              ${this._preview.error}
              <ha-button slot="action" appearance="plain" size="s" @click=${() => this._queue.now(this._draft)}>Retry</ha-button>
            </ha-alert>` : d}
        ${i.length ? o`<ha-alert alert-type="warning">
              ${O(i.length, "widget")} ${i.length === 1 ? "doesn't" : "don't"} fit
              this layout and ${i.length === 1 ? "is" : "are"} hidden.
              <ha-button
                slot="action"
                appearance="plain"
                size="s"
                @click=${() => this._edit(Rt(this._draft, this._slotCount))}
                >Remove hidden widgets</ha-button
              >
            </ha-alert>` : d}
      </div>
    `;
  }
  _renderInspector() {
    const t = (e, i) => o`<button
      role="tab"
      class="reset tab ${this._tab === e ? "active" : ""}"
      aria-selected=${this._tab === e ? "true" : "false"}
      @click=${() => {
      this._tab = e, e === "view" && this._scheduleThemeTiles();
    }}
    >
      ${i}
    </button>`;
    return o`
      <ha-card outlined>
        <div class="tabs" role="tablist">
          ${t("widget", `Slot ${this._slot + 1}`)} ${t("view", "Layout & theme")}
        </div>
        <div class="panel" role="tabpanel">
          ${this._tab === "widget" ? this._renderWidgetTab() : this._renderViewTab()}
        </div>
      </ha-card>
    `;
  }
  _renderWidgetTab() {
    const t = F(this._draft, this._slot), e = t != null && t.type ? this.config.widget_types[t.type] : void 0;
    return !(t != null && t.type) || !e || this._changingType ? this._renderPicker(t == null ? void 0 : t.type) : this._renderWidget(t, e);
  }
  _badge(t, e = 40) {
    const i = Ue[(t == null ? void 0 : t.category) ?? "custom"] ?? Ue.custom;
    return o`<span class="icon-badge" style="--size:${e}px;--badge-color:${i}"
      ><ha-icon .icon=${(t == null ? void 0 : t.icon) ?? "mdi:widgets"}></ha-icon
    ></span>`;
  }
  _renderPicker(t) {
    const e = Object.entries(this.config.widget_types), i = Fe.map((h) => ({
      category: h,
      items: e.filter(([, p]) => (p.category ?? "custom") === h)
    })).filter((h) => h.items.length), s = e.filter(([, h]) => h.category && !Fe.includes(h.category));
    s.length && i.push({ category: "custom", items: s });
    const [, , r, a] = this._rects()[this._slot] ?? [0, 0, 1, 1], [n, c] = [r * 240, a * 240], l = li(ot(n, c));
    return o`
      <div class="picker-head">
        <div>
          <h3>${t ? "Change widget" : `Add a widget to slot ${this._slot + 1}`}</h3>
          <p class="muted">${t ? "The entity and label carry over." : "Pick what this cell shows."}</p>
        </div>
        ${t ? o`<ha-button appearance="plain" @click=${() => this._changingType = !1}>Cancel</ha-button>` : d}
      </div>
      ${i.map(
      (h) => o`<div class="group">
          <div class="group-title">${Vt[h.category] ?? "Other"}</div>
          <div class="tiles">
            ${h.items.map(
        ([p, g]) => o`<button
                class="reset tile focus-ring ${p === t ? "current" : ""}"
                aria-label=${g.name}
                @click=${() => this._pickType(p)}
              >
                ${this._renderTilePreview(p, g, n, c, l)}
                <span class="tile-text">
                  <span class="tile-name">${g.name}</span>
                  <span class="tile-desc">${g.description ?? ""}</span>
                </span>
              </button>`
      )}
          </div>
        </div>`
    )}
    `;
  }
  _renderTilePreview(t, e, i, s, r) {
    const a = oi(this.previews.url, this.previews.version, t, i, s), n = a && !this._brokenPreviews.has(a);
    return o`<span class="tile-preview">
      ${n ? o`<img
            src=${a}
            alt=""
            loading="lazy"
            style=${r ? `aspect-ratio:${r[0]}/${r[1]}` : ""}
            @error=${() => this._brokenPreviews = new Set(this._brokenPreviews).add(a)}
          />` : this._badge(e, 40)}
    </span>`;
  }
  _renderMiniMap() {
    const t = this._rects();
    return t.length < 2 ? d : o`<div class="position">
      <span class="caption">Position</span>
      <div class="minimap" role="group" aria-label="Move to slot">
        ${t.map(
      ([e, i, s, r], a) => o`<button
            class="reset mini ${a === this._slot ? "here" : ""}"
            style="left:${e * 100}%;top:${i * 100}%;width:${s * 100}%;height:${r * 100}%"
            aria-label=${a === this._slot ? `Slot ${a + 1} (here)` : `Move to slot ${a + 1}`}
            title=${a === this._slot ? "Here" : `Move to slot ${a + 1} (swaps)`}
            @click=${() => {
        a !== this._slot && (this._edit(He(this._draft, this._slot, a)), this._slot = a);
      }}
          ></button>`
    )}
      </div>
    </div>`;
  }
  _renderWidget(t, e) {
    var s;
    const i = this._slot;
    return o`
      <div class="widget-head">
        ${this._badge(e)}
        <div class="grow">
          <h3>${e.name}</h3>
          <p class="muted ellipsis">${e.description ?? ""}</p>
        </div>
        <ha-button appearance="plain" size="s" @click=${() => this._changingType = !0}>Change</ha-button>
        <gm-menu
          .items=${[{ key: "clear", label: "Clear slot", icon: "mdi:close-circle-outline", danger: !0 }]}
          @action=${() => this._edit(Nt(this._draft, i))}
        ></gm-menu>
      </div>
      ${this._renderMiniMap()}
      ${e.needs_entity ? o`<ha-selector
            class="entity-field"
            .hass=${this.hass}
            .selector=${{ entity: e.entity_domains ? { domain: e.entity_domains } : {} }}
            .value=${t.entity_id ?? ""}
            .label=${"Entity"}
            .required=${!0}
            @value-changed=${(r) => this._edit(ye(this._draft, i, { entity_id: r.detail.value || void 0 }))}
          ></ha-selector>` : d}
      ${e.uses_label === !1 ? d : o`<ha-input
            class="label-input"
            label="Label"
            hint="Optional. Supports templates."
            .value=${t.label ?? ""}
            @input=${(r) => this._edit(ye(this._draft, i, { label: r.target.value }))}
          ></ha-input>`}
      ${(s = e.options) != null && s.length ? o`<gm-widget-options
            .hass=${this.hass}
            .schema=${e}
            .widget=${t}
            @option-change=${(r) => this._edit(Mt(this._draft, i, r.detail.key, r.detail.value))}
          ></gm-widget-options>` : d}
    `;
  }
  _renderViewTab() {
    const t = Object.entries(this.config.layout_types);
    return o`
      <div class="group">
        <div class="group-title">Layout</div>
        <div class="layout-tiles" role="radiogroup" aria-label="Layout">
          ${t.map(
      ([e, i]) => o`<button
              class="reset layout-tile focus-ring ${this._draft.layout === e ? "current" : ""}"
              role="radio"
              aria-checked=${this._draft.layout === e ? "true" : "false"}
              aria-label=${i.name}
              title="${i.name} · ${O(i.slots, "slot")}"
              @click=${() => this._setLayout(e)}
            >
              <svg viewBox="0 0 1 1" aria-hidden="true">
                ${i.rects.map(
        ([s, r, a, n]) => bt`<rect x=${s + 0.01} y=${r + 0.01} width=${Math.max(a - 0.02, 0.01)} height=${Math.max(n - 0.02, 0.01)} rx="0.04"></rect>`
      )}
              </svg>
              <span class="tile-name">${i.name}</span>
              <span class="tile-desc">${O(i.slots, "slot")}</span>
            </button>`
    )}
        </div>
      </div>
      <div class="group">
        <div class="group-title">Theme</div>
        <div class="theme-tiles" role="radiogroup" aria-label="Theme">
          ${Object.entries(this.config.themes).map(([e, i]) => {
      const s = this._themeTile(e);
      return o`<button
              class="reset theme-tile focus-ring ${this._draft.theme === e ? "current" : ""}"
              role="radio"
              aria-checked=${this._draft.theme === e ? "true" : "false"}
              aria-label=${i}
              @click=${() => this._edit({ ...this._draft, theme: e })}
            >
              ${s ? o`<img src=${s} alt="" />` : o`<span class="skeleton"></span>`}
              <span class="tile-name">${i}</span>
            </button>`;
    })}
        </div>
      </div>
    `;
  }
};
_.styles = [
  re,
  P`
      :host {
        display: flex;
        flex-direction: column;
        height: 100%;
      }
      .toolbar {
        display: flex;
        align-items: center;
        gap: 8px;
        height: var(--header-height, 56px);
        padding: 0 12px 0 4px;
        flex: none;
        background: var(--app-header-background-color, var(--primary-background-color));
        color: var(--app-header-text-color, var(--primary-text-color));
        border-bottom: var(--app-header-border-bottom, 1px solid var(--divider-color));
      }
      .title-input {
        flex: 1;
        min-width: 0;
        font: inherit;
        font-size: 20px;
        line-height: 28px;
        color: inherit;
        background: transparent;
        border: 0;
        border-bottom: 2px solid transparent;
        padding: 4px 4px 2px;
        border-radius: 4px 4px 0 0;
      }
      .title-input:hover {
        border-bottom-color: var(--divider-color);
      }
      .title-input:focus {
        outline: none;
        border-bottom-color: var(--primary-color);
        background: var(--secondary-background-color);
      }
      .unsaved {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: var(--secondary-text-color);
        white-space: nowrap;
      }
      .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--warning-color, #ffa600);
      }
      .content {
        flex: 1;
        overflow: auto;
      }
      .layout {
        max-width: 1280px;
        margin: 0 auto;
        padding: 24px;
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        gap: 32px;
        align-items: start;
      }
      .narrow .layout {
        grid-template-columns: minmax(0, 1fr);
        padding: 0 12px 24px;
        gap: 12px;
      }
      .narrow .unsaved-text {
        display: none;
      }
      .stage {
        position: sticky;
        top: 24px;
      }
      .narrow .stage {
        top: 0;
        z-index: 2;
        margin: 0 -12px;
        padding: 12px 12px 8px;
        background: var(--primary-background-color);
        border-bottom: 1px solid var(--divider-color);
      }
      .stage-inner {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
      }
      .wide .stage-inner {
        align-items: flex-start;
      }
      .stage-inner ha-alert {
        width: 100%;
        max-width: 528px;
      }
      .stage-caption {
        text-align: center;
        font-size: 14px;
        line-height: 20px;
      }
      .wide .stage-caption {
        text-align: left;
      }
      .narrow .stage-caption {
        display: none;
      }
      .overlay {
        position: absolute;
        inset: 0;
      }
      .slot-hit {
        position: absolute;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        margin: 0;
        border: 0;
        border-radius: 6px;
        background: transparent;
        cursor: pointer;
        color: rgba(255, 255, 255, 0.85);
        --mdc-icon-size: 28px;
        transition: box-shadow 0.12s, background 0.12s;
      }
      .slot-hit:hover {
        box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.55);
      }
      .slot-hit.empty {
        box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.28);
        background-image: linear-gradient(rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.06));
        outline: 1px dashed rgba(255, 255, 255, 0.45);
        outline-offset: -5px;
      }
      .slot-hit.selected {
        box-shadow:
          inset 0 0 0 3px var(--primary-color),
          0 0 0 1px rgba(0, 0, 0, 0.4);
        background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.12);
      }
      .slot-hit.drop {
        box-shadow: inset 0 0 0 2px var(--accent-color, var(--primary-color));
      }
      .slot-hit:focus-visible {
        outline: 2px solid #fff;
        outline-offset: -6px;
      }
      .screen-empty {
        display: flex;
        align-items: center;
        justify-content: center;
      }
      ha-card {
        overflow: hidden;
      }
      .tabs {
        display: flex;
        border-bottom: 1px solid var(--divider-color);
        padding: 0 8px;
      }
      .tab {
        position: relative;
        padding: 14px 16px;
        font-size: 14px;
        font-weight: 500;
        color: var(--secondary-text-color);
      }
      .tab.active {
        color: var(--primary-color);
      }
      .tab.active::after {
        content: "";
        position: absolute;
        left: 12px;
        right: 12px;
        bottom: 0;
        height: 3px;
        border-radius: 3px 3px 0 0;
        background: var(--primary-color);
      }
      .panel {
        display: flex;
        flex-direction: column;
        gap: 20px;
        padding: 20px;
      }
      .narrow .panel {
        padding: 16px;
      }
      h3 {
        font-size: 16px;
        font-weight: 500;
        line-height: 24px;
      }
      .muted {
        font-size: 13px;
      }
      .picker-head,
      .widget-head {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .picker-head > div {
        flex: 1;
      }
      .group {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .group-title,
      .caption {
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--secondary-text-color);
      }
      .tiles {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 10px;
      }
      .tile {
        display: flex;
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
        padding: 8px 8px 10px;
        border: 1px solid var(--divider-color);
        border-radius: 12px;
        background: var(--card-background-color);
        text-align: left;
        transition: background 0.12s, border-color 0.12s;
      }
      /* A little screen: the widget as it renders in a cell this size. */
      .tile-preview {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 104px;
        padding: 6px;
        border-radius: 8px;
        background: #000;
        box-sizing: border-box;
      }
      .tile-preview img {
        display: block;
        max-width: 100%;
        max-height: 100%;
        border-radius: 4px;
      }
      .tile .tile-text {
        padding: 0 4px;
      }
      .tile:hover {
        background: var(--secondary-background-color);
      }
      .tile.current,
      .layout-tile.current,
      .theme-tile.current {
        border-color: var(--primary-color);
        box-shadow: inset 0 0 0 1px var(--primary-color);
        background: var(--gm-tint);
      }
      .tile-text {
        display: flex;
        flex-direction: column;
        min-width: 0;
      }
      .tile-name {
        font-size: 14px;
        font-weight: 500;
        color: var(--primary-text-color);
      }
      .tile-desc {
        font-size: 12px;
        line-height: 16px;
        color: var(--secondary-text-color);
      }
      .position {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .minimap {
        position: relative;
        width: 64px;
        height: 64px;
        border-radius: 8px;
        background: var(--gm-bezel);
      }
      .mini {
        position: absolute;
        padding: 0;
        border: 2px solid var(--gm-bezel);
        border-radius: 5px;
        background: rgba(255, 255, 255, 0.22);
        cursor: pointer;
      }
      .mini:hover {
        background: rgba(255, 255, 255, 0.45);
      }
      .mini.here {
        background: var(--primary-color);
        cursor: default;
      }
      .entity-field,
      .label-input {
        display: block;
      }
      .layout-tiles {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
        gap: 8px;
      }
      .layout-tile,
      .theme-tile {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        padding: 10px 6px 8px;
        border: 1px solid var(--divider-color);
        border-radius: 12px;
        text-align: center;
      }
      .layout-tile:hover,
      .theme-tile:hover {
        background: var(--secondary-background-color);
      }
      .layout-tile svg {
        width: 44px;
        height: 44px;
        border-radius: 6px;
        background: var(--gm-bezel);
        padding: 2px;
      }
      .layout-tile rect {
        fill: rgba(255, 255, 255, 0.55);
      }
      .layout-tile.current rect {
        fill: var(--primary-color);
      }
      .layout-tile .tile-name {
        font-size: 12px;
        line-height: 16px;
      }
      .layout-tile .tile-desc {
        font-size: 11px;
      }
      .theme-tiles {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
        gap: 8px;
      }
      .theme-tile img,
      .theme-tile .skeleton {
        display: block;
        width: 100%;
        aspect-ratio: 1;
        border-radius: 6px;
        background-color: #000;
      }
      .theme-tile .tile-name {
        font-size: 12px;
      }
    `
];
$([
  m({ attribute: !1 })
], _.prototype, "hass", 2);
$([
  m({ attribute: !1 })
], _.prototype, "config", 2);
$([
  m({ attribute: !1 })
], _.prototype, "api", 2);
$([
  m({ attribute: !1 })
], _.prototype, "view", 2);
$([
  m({ attribute: !1 })
], _.prototype, "previews", 2);
$([
  u()
], _.prototype, "_draft", 2);
$([
  u()
], _.prototype, "_saved", 2);
$([
  u()
], _.prototype, "_slot", 2);
$([
  u()
], _.prototype, "_tab", 2);
$([
  u()
], _.prototype, "_changingType", 2);
$([
  u()
], _.prototype, "_brokenPreviews", 2);
$([
  u()
], _.prototype, "_saving", 2);
$([
  u()
], _.prototype, "_discardOpen", 2);
$([
  u()
], _.prototype, "_preview", 2);
$([
  u()
], _.prototype, "_themeTiles", 2);
$([
  u()
], _.prototype, "_width", 2);
$([
  u()
], _.prototype, "_dragFrom", 2);
_ = $([
  N("gm-view-editor")
], _);
const _e = (t) => typeof t == "object" && t !== null && !Array.isArray(t);
function yi(t) {
  const e = /```[^\n`]*\n([\s\S]*?)```/.exec(t);
  return (e ? e[1] : t).trim();
}
function $i(t) {
  const e = yi(t);
  if (!e) return { error: "Paste a view's JSON." };
  let i;
  try {
    i = JSON.parse(e);
  } catch (s) {
    return { error: `This isn't valid JSON: ${s instanceof Error ? s.message : String(s)}` };
  }
  return _e(i) && !("layout" in i) && _e(i.view) && (i = i.view), _e(i) ? { view: i } : { error: "A view is a JSON object with a layout and widgets." };
}
function wi(t) {
  return t.filter((e) => !e.exists);
}
function xi(t) {
  return Object.fromEntries(
    Object.entries(t).filter(([e, i]) => i && i !== e)
  );
}
function ki(t, e) {
  const i = typeof t.name == "string" ? t.name.trim() : "";
  return it(e, i || "Imported view");
}
function Ge(t) {
  return {
    layout: String(t.layout ?? ""),
    theme: typeof t.theme == "string" && t.theme ? t.theme : "watchos",
    widgets: Array.isArray(t.widgets) ? t.widgets : []
  };
}
var Ai = Object.defineProperty, Ei = Object.getOwnPropertyDescriptor, w = (t, e, i, s) => {
  for (var r = s > 1 ? void 0 : s ? Ei(e, i) : e, a = t.length - 1, n; a >= 0; a--)
    (n = t[a]) && (r = (s ? n(e, i, r) : n(r)) || r);
  return s && r && Ai(e, i, r), r;
};
const J = "new";
let y = class extends E {
  constructor() {
    super(...arguments), this.views = [], this._text = "", this._parseError = null, this._source = null, this._check = null, this._checkError = null, this._missing = [], this._picks = {}, this._name = "", this._target = J, this._saving = !1, this._saveError = null, this._preview = {
      result: null,
      loading: !1,
      error: null
    }, this._checkSeq = 0, this._queue = this._newQueue();
  }
  _newQueue() {
    return new et(
      (t) => this.api.render(t),
      (t) => this._preview = t
    );
  }
  /** Drop the preview (and any render in flight): nothing valid to show. */
  _clearPreview() {
    this._queue.dispose(), this._queue = this._newQueue(), this._preview = { result: null, loading: !1, error: null };
  }
  disconnectedCallback() {
    clearTimeout(this._parseTimer), this._queue.dispose(), this._checkSeq += 1, super.disconnectedCallback();
  }
  firstUpdated() {
    var t;
    (t = this.renderRoot.querySelector("textarea")) == null || t.focus();
  }
  // ---- input ---------------------------------------------------------------------------
  _onText(t) {
    this._text = t, clearTimeout(this._parseTimer), this._parseTimer = setTimeout(() => void this._parse(), 300);
  }
  async _parse() {
    const t = $i(this._text);
    if (this._checkSeq += 1, this._picks = {}, this._missing = [], this._check = null, this._checkError = null, this._saveError = null, t.error !== void 0) {
      this._source = null, this._parseError = this._text.trim() ? t.error : null, this._clearPreview();
      return;
    }
    this._parseError = null, this._source = t.view, this._name = ki(t.view, this.views);
    const e = await this._runCheck();
    e && (this._missing = wi(e.entities));
  }
  _pick(t, e) {
    this._picks = { ...this._picks, [t]: e }, this._runCheck();
  }
  /** Check the pasted view with the current picks; latest call wins. */
  async _runCheck() {
    if (!this._source) return null;
    const t = ++this._checkSeq;
    try {
      const e = await this.api.checkView(this._source, xi(this._picks));
      return t !== this._checkSeq ? null : (this._check = e, this._checkError = null, e.errors.length ? this._clearPreview() : this._queue.request(Ge(e.view)), e);
    } catch (e) {
      return t !== this._checkSeq || (this._checkError = S(e)), null;
    }
  }
  // ---- save ----------------------------------------------------------------------------
  get _canSave() {
    const t = this._check;
    return !t || t.errors.length || this._saving ? !1 : this._target !== J || !!this._name.trim();
  }
  async _save() {
    const t = this._check;
    if (!t || !this._canSave) return;
    this._saving = !0, this._saveError = null;
    const e = Ge(t.view);
    try {
      const i = this._target !== J, s = i ? await this.api.replaceView(this._target, e) : await this.api.importView(this._name.trim(), e);
      this.dispatchEvent(new CustomEvent("imported", { detail: { view: s, replaced: i } }));
    } catch (i) {
      this._saveError = `Couldn't save the view: ${S(i)}`;
    } finally {
      this._saving = !1;
    }
  }
  _cancel() {
    this._saving || this.dispatchEvent(new CustomEvent("cancel"));
  }
  // ---- render --------------------------------------------------------------------------
  render() {
    var e;
    const t = this.views.find((i) => i.id === this._target);
    return o`<gm-dialog open wide heading="Import a view" @cancel=${this._cancel}>
      <div class="import">
        <div class="source">
          <label class="field-label" for="json">View JSON</label>
          <textarea
            id="json"
            class="import-json"
            spellcheck="false"
            placeholder='{"layout": "grid_2x2", "theme": "watchos", "widgets": [...]}'
            .value=${this._text}
            @input=${(i) => this._onText(i.target.value)}
          ></textarea>
          <p class="hint">
            Paste a view from an AI or from <code>render_view.py --save-view</code>. Code fences are fine.
          </p>
          ${this._parseError ? o`<ha-alert alert-type="error">${this._parseError}</ha-alert>` : d}
          ${this._checkError ? o`<ha-alert alert-type="error" title="Couldn't check the view">${this._checkError}</ha-alert>` : d}
          ${this._renderProblems()} ${this._renderMapping()}
        </div>
        <div class="side">
          <gm-screen
            .src=${this._preview.result ? te(this._preview.result.image) : null}
            .size=${240}
            img-class="import-preview"
            alt="Preview of the imported view"
            ?busy=${this._preview.loading}
          >
            <span slot="empty" class="empty"
              >${this._source ? (e = this._check) != null && e.errors.length ? "No preview: fix the errors" : "Rendering…" : "Preview"}</span
            >
          </gm-screen>
          ${this._preview.error ? o`<ha-alert alert-type="error" title="Preview failed">${this._preview.error}</ha-alert>` : d}
          ${this._renderTarget()}
        </div>
      </div>
      ${this._saveError ? o`<ha-alert alert-type="error">${this._saveError}</ha-alert>` : d}
      <ha-button slot="actions" appearance="plain" ?disabled=${this._saving} @click=${this._cancel}>Cancel</ha-button>
      <ha-button
        slot="actions"
        class="import-save"
        variant=${t ? "danger" : "brand"}
        appearance="accent"
        ?disabled=${!this._canSave}
        .loading=${this._saving}
        @click=${() => this._save()}
        >${t ? `Replace "${t.name}"` : "Save as new view"}</ha-button
      >
    </gm-dialog>`;
  }
  _renderProblems() {
    const t = this._check;
    return t ? o`
      ${t.errors.length ? o`<ha-alert alert-type="error" title="This view can't be imported">
            <ul>
              ${t.errors.map((e) => o`<li>${e}</li>`)}
            </ul>
          </ha-alert>` : d}
      ${t.warnings.length ? o`<ha-alert alert-type="warning" title=${O(t.warnings.length, "warning")}>
            <ul>
              ${t.warnings.map((e) => o`<li>${e}</li>`)}
            </ul>
          </ha-alert>` : d}
    ` : d;
  }
  _renderMapping() {
    return this._missing.length ? o`<section class="mapping">
      <h3>Entities to map</h3>
      <p class="hint">
        ${O(this._missing.length, "entity isn't", "entities aren't")} in this Home Assistant. Pick yours;
        every use in the view follows, templates included.
      </p>
      ${this._missing.map(
      (t) => o`<div class="map-row" data-entity-id=${t.id}>
          <code class="from">${t.id}</code>
          <ha-selector
            .hass=${this.hass}
            .selector=${{ entity: { domain: t.domain } }}
            .value=${this._picks[t.id] ?? ""}
            .label=${`Your ${t.domain.replace(/_/g, " ")}`}
            .required=${!1}
            @value-changed=${(e) => this._pick(t.id, e.detail.value ?? "")}
          ></ha-selector>
        </div>`
    )}
    </section>` : d;
  }
  _renderTarget() {
    const t = [
      { value: J, label: "A new view" },
      ...this.views.map((i) => ({ value: i.id, label: `Replace "${i.name}"` }))
    ], e = t.map((i) => i.value);
    return o`<div class="target">
      <ha-select
        .label=${"Save as"}
        .value=${this._target}
        .options=${t}
        @selected=${(i) => {
      const s = Ee(i.detail, e);
      s !== void 0 && (this._target = s);
    }}
        @closed=${(i) => i.stopPropagation()}
      >
        ${t.map((i) => o`<mwc-list-item value=${i.value}>${i.label}</mwc-list-item>`)}
      </ha-select>
      ${this._target === J ? o`<ha-input
            class="import-name"
            label="Name"
            .value=${this._name}
            @input=${(i) => this._name = i.target.value}
          ></ha-input>` : o`<p class="hint">Keeps its name and the displays showing it; its layout, theme and widgets are replaced.</p>`}
    </div>`;
  }
};
y.styles = [
  re,
  P`
      .import {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 264px;
        gap: 24px;
        color: var(--primary-text-color);
      }
      @media (max-width: 720px) {
        .import {
          grid-template-columns: minmax(0, 1fr);
        }
      }
      .source,
      .side,
      .target,
      .mapping {
        display: flex;
        flex-direction: column;
        gap: 12px;
        min-width: 0;
      }
      .side {
        align-items: center;
      }
      .target {
        align-self: stretch;
      }
      .field-label {
        font-size: 14px;
        font-weight: 500;
      }
      textarea {
        width: 100%;
        min-height: 200px;
        resize: vertical;
        padding: 12px;
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        background: var(--secondary-background-color, transparent);
        color: var(--primary-text-color);
        font: 12px/1.45 var(--ha-font-family-code, ui-monospace, Menlo, monospace);
      }
      textarea:focus {
        outline: 2px solid var(--primary-color);
        outline-offset: -1px;
      }
      .hint {
        font-size: 13px;
        line-height: 18px;
        color: var(--secondary-text-color);
      }
      code {
        font-family: var(--ha-font-family-code, ui-monospace, Menlo, monospace);
        font-size: 12px;
      }
      h3 {
        font-size: 15px;
        font-weight: 500;
      }
      .map-row {
        display: grid;
        grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr);
        align-items: end;
        gap: 12px;
      }
      .map-row .from {
        padding-bottom: 20px;
        overflow-wrap: anywhere;
        color: var(--secondary-text-color);
      }
      ha-alert ul {
        margin: 4px 0 0;
        padding-left: 18px;
      }
      ha-alert,
      ha-select,
      ha-input {
        display: block;
        width: 100%;
      }
      .empty {
        color: rgba(255, 255, 255, 0.5);
        font-size: 13px;
      }
    `
];
w([
  m({ attribute: !1 })
], y.prototype, "hass", 2);
w([
  m({ attribute: !1 })
], y.prototype, "api", 2);
w([
  m({ attribute: !1 })
], y.prototype, "views", 2);
w([
  u()
], y.prototype, "_text", 2);
w([
  u()
], y.prototype, "_parseError", 2);
w([
  u()
], y.prototype, "_source", 2);
w([
  u()
], y.prototype, "_check", 2);
w([
  u()
], y.prototype, "_checkError", 2);
w([
  u()
], y.prototype, "_missing", 2);
w([
  u()
], y.prototype, "_picks", 2);
w([
  u()
], y.prototype, "_name", 2);
w([
  u()
], y.prototype, "_target", 2);
w([
  u()
], y.prototype, "_saving", 2);
w([
  u()
], y.prototype, "_saveError", 2);
w([
  u()
], y.prototype, "_preview", 2);
y = w([
  N("gm-import-dialog")
], y);
var Si = Object.defineProperty, Ci = Object.getOwnPropertyDescriptor, b = (t, e, i, s) => {
  for (var r = s > 1 ? void 0 : s ? Ci(e, i) : e, a = t.length - 1, n; a >= 0; a--)
    (n = t[a]) && (r = (s ? n(e, i, r) : n(r)) || r);
  return s && r && Si(e, i, r), r;
};
const fe = (t) => JSON.stringify([t.layout, t.theme, t.widgets]), Oi = 3e4;
let v = class extends E {
  constructor() {
    super(...arguments), this.narrow = !1, this._config = null, this._views = [], this._devices = [], this._loadError = null, this._editing = null, this._thumbs = /* @__PURE__ */ new Map(), this._failedThumbs = /* @__PURE__ */ new Set(), this._createOpen = !1, this._newName = "", this._creating = !1, this._createError = null, this._deleting = null, this._importOpen = !1, this._width = 1200, this._api = new Pt(() => this.hass), this._thumbKeys = /* @__PURE__ */ new Map(), this._watched = /* @__PURE__ */ new Map(), this._thumbsRefreshing = !1, this._resize = new ResizeObserver((t) => {
      var e;
      this._width = ((e = t[0]) == null ? void 0 : e.contentRect.width) ?? this._width;
    }), this._warnBeforeUnload = (t) => {
      var e;
      (e = this._editor) != null && e.dirty && t.preventDefault();
    }, this._onVisible = () => {
      document.visibilityState === "visible" && (this._refreshDevices(), this._refreshThumbs());
    };
  }
  // ---- lifecycle -----------------------------------------------------------------
  connectedCallback() {
    super.connectedCallback(), window.addEventListener("beforeunload", this._warnBeforeUnload), document.addEventListener("visibilitychange", this._onVisible), this._resize.observe(this), this._stopMinute = st(() => this._refreshThumbs());
  }
  disconnectedCallback() {
    var t;
    window.removeEventListener("beforeunload", this._warnBeforeUnload), document.removeEventListener("visibilitychange", this._onVisible), this._resize.disconnect(), clearTimeout(this._devicesTimer), (t = this._stopMinute) == null || t.call(this), clearInterval(this._recheck), this._recheck = void 0, super.disconnectedCallback();
  }
  firstUpdated() {
    this._load();
  }
  willUpdate(t) {
    var e, i;
    if (t.has("hass") && this.hass) {
      let s = !1;
      for (const r of this._devices)
        for (const a of [(e = r.entities) == null ? void 0 : e.preview, (i = r.entities) == null ? void 0 : i.display]) {
          if (!a) continue;
          const n = this.hass.states[a];
          this._watched.has(a) && this._watched.get(a) !== n && (s = !0), this._watched.set(a, n);
        }
      s && this._refreshDevices();
    }
  }
  updated(t) {
    t.has("_devices") && this._syncRecheck();
  }
  /** Re-check devices/list periodically, only while a display isn't loaded. */
  _syncRecheck() {
    const t = this.isConnected && Bt(this._devices);
    t && !this._recheck ? this._recheck = setInterval(() => {
      document.visibilityState === "visible" && this._refreshDevices();
    }, Oi) : !t && this._recheck && (clearInterval(this._recheck), this._recheck = void 0);
  }
  get _editor() {
    var t;
    return ((t = this.renderRoot) == null ? void 0 : t.querySelector("gm-view-editor")) ?? null;
  }
  // ---- data ------------------------------------------------------------------------
  _notify(t) {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message: t }, bubbles: !0, composed: !0 })
    );
  }
  async _load() {
    try {
      const [t, e, i] = await Promise.all([
        this._api.config(),
        this._api.views(),
        this._api.devices()
      ]);
      this._config = t, this._views = e, this._devices = i, this._loadError = null, this._renderThumbs();
    } catch (t) {
      this._loadError = S(t);
    }
  }
  _refreshDevices() {
    clearTimeout(this._devicesTimer), this._devicesTimer = setTimeout(async () => {
      try {
        this._devices = await this._api.devices();
      } catch {
      }
    }, 300);
  }
  /** Render thumbnails for views that are new or changed (3 at a time). */
  async _renderThumbs() {
    const t = this._views.filter((e) => this._thumbKeys.get(e.id) !== fe(e));
    for (const e of t) this._thumbKeys.set(e.id, fe(e));
    await be(t, 3, async (e) => {
      try {
        const i = await this._api.render(e);
        if (this._thumbs = new Map(this._thumbs).set(e.id, te(i.image)), this._failedThumbs.has(e.id)) {
          const s = new Set(this._failedThumbs);
          s.delete(e.id), this._failedThumbs = s;
        }
      } catch {
        this._failedThumbs = new Set(this._failedThumbs).add(e.id);
      }
    });
  }
  /**
   * Re-render every thumbnail in place (each keeps its image until the new
   * one arrives). Only while the list is on screen and the tab visible.
   */
  _refreshThumbs() {
    document.visibilityState !== "visible" || this._editing || this._thumbsRefreshing || (this._thumbsRefreshing = !0, be([...this._views], 3, async (t) => {
      const e = fe(t);
      try {
        const i = await this._api.render(t);
        this._thumbKeys.get(t.id) === e && (this._thumbs = new Map(this._thumbs).set(t.id, te(i.image)));
      } catch {
      }
    }).finally(() => this._thumbsRefreshing = !1));
  }
  // ---- view actions -------------------------------------------------------------------
  _openCreate() {
    this._newName = it(this._views), this._createError = null, this._createOpen = !0, this.updateComplete.then(
      () => {
        var t;
        return (t = this.renderRoot.querySelector(".create-view-name")) == null ? void 0 : t.focus();
      }
    );
  }
  async _create() {
    const t = this._newName.trim();
    if (!(!t || this._creating)) {
      this._creating = !0, this._createError = null;
      try {
        const e = await this._api.createView(t);
        this._views = [...this._views, e], this._createOpen = !1, this._editing = e;
      } catch (e) {
        this._createError = `Couldn't create the view: ${S(e)}`;
      } finally {
        this._creating = !1;
      }
    }
  }
  _onImported({ view: t, replaced: e }) {
    this._importOpen = !1, this._views = e ? this._views.map((i) => i.id === t.id ? t : i) : [...this._views, t], this._renderThumbs(), this._notify(e ? `Replaced "${t.name}"` : `Imported "${t.name}"`);
  }
  async _duplicate(t) {
    try {
      const e = await this._api.duplicateView(t.id);
      this._views = [...this._views, e], this._renderThumbs();
    } catch (e) {
      this._notify(`Couldn't duplicate "${t.name}": ${S(e)}`);
    }
  }
  async _delete(t) {
    this._deleting = null;
    try {
      await this._api.deleteView(t.id), this._views = this._views.filter((e) => e.id !== t.id), this._notify(`Deleted "${t.name}"`), this._refreshDevices();
    } catch (e) {
      this._notify(`Couldn't delete "${t.name}": ${S(e)}`);
    }
  }
  _onSaved(t) {
    this._views = this._views.map((e) => e.id === t.id ? t : e), this._renderThumbs();
  }
  _devicesShowing(t) {
    return this._devices.filter((e) => e.assigned_views.includes(t));
  }
  // ---- render ------------------------------------------------------------------------------
  render() {
    var t, e, i, s;
    return this._editing && this._config ? o`<gm-view-editor
        .hass=${this.hass}
        .config=${this._config}
        .api=${this._api}
        .view=${this._editing}
        .previews=${{
      url: String(((e = (t = this.panel) == null ? void 0 : t.config) == null ? void 0 : e.previews_url) ?? "/geekmagic_previews"),
      version: String(((s = (i = this.panel) == null ? void 0 : i.config) == null ? void 0 : s.previews_hash) ?? "dev")
    }}
        @saved=${(r) => this._onSaved(r.detail)}
        @leave=${() => this._editing = null}
      ></gm-view-editor>` : o`
      <div class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div class="title">GeekMagic</div>
      </div>
      <div class="content">${this._renderMain()}</div>
      ${this._config ? o`<ha-button class="fab" variant="brand" appearance="accent" size="l" @click=${this._openCreate}>
            <ha-svg-icon slot="start" .path=${x.plus}></ha-svg-icon>Add view
          </ha-button>` : d}
      ${this._renderCreateDialog()} ${this._renderDeleteDialog()}
      ${this._importOpen ? o`<gm-import-dialog
            .hass=${this.hass}
            .api=${this._api}
            .views=${this._views}
            @imported=${(r) => this._onImported(r.detail)}
            @cancel=${() => this._importOpen = !1}
          ></gm-import-dialog>` : d}
    `;
  }
  _renderMain() {
    if (this._loadError)
      return o`<div class="page">
        <ha-alert alert-type="error" title="Couldn't load GeekMagic">
          ${this._loadError}
          <ha-button slot="action" appearance="plain" @click=${() => this._load()}>Retry</ha-button>
        </ha-alert>
      </div>`;
    if (!this._config)
      return o`<div class="loading"><ha-spinner></ha-spinner></div>`;
    const t = this._width < 700;
    return o`<div class="page ${t ? "narrow" : ""}">
      <section>
        <h2 class="section-title">
          ${this._devices.length === 1 ? "Display" : "Displays"}
          ${this._devices.length > 1 ? o`<span class="count">${this._devices.length}</span>` : d}
        </h2>
        ${this._devices.length ? o`<div class="devices">
              ${this._devices.map(
      (e) => o`<gm-device-card
                  .hass=${this.hass}
                  .api=${this._api}
                  .device=${e}
                  .views=${this._views}
                  .thumbs=${this._thumbs}
                  .narrow=${t}
                  @devices-changed=${() => this._refreshDevices()}
                  @edit-view=${(i) => {
        const s = this._views.find((r) => r.id === i.detail);
        s && (this._editing = s);
      }}
                ></gm-device-card>`
    )}
            </div>` : o`<ha-alert alert-type="info" title="No displays yet">
              Add your GeekMagic display in
              <a href="/config/integrations/integration/geekmagic">Settings → Devices &amp; services</a>,
              then pick the views it shows here.
            </ha-alert>`}
      </section>
      <section>
        <div class="views-head">
          <h2 class="section-title">Views <span class="count">${this._views.length}</span></h2>
          <ha-button class="import-view" appearance="plain" @click=${() => this._importOpen = !0}>
            <ha-icon slot="start" icon="mdi:import"></ha-icon>Import view
          </ha-button>
        </div>
        ${this._views.length ? o`<div class="views">${this._views.map((e) => this._renderViewCard(e))}</div>` : o`<div class="empty">
              <ha-icon icon="mdi:view-dashboard-edit-outline"></ha-icon>
              <h3>Create your first view</h3>
              <p class="muted">A view is one screen: a layout, a theme, and the widgets in it.</p>
              <ha-button variant="brand" appearance="accent" @click=${this._openCreate}>Create a view</ha-button>
            </div>`}
      </section>
    </div>`;
  }
  _renderViewCard(t) {
    const e = this._thumbs.get(t.id), i = this._devicesShowing(t.id);
    return o`<ha-card outlined class="view-card" @click=${() => this._editing = t}>
      <button class="reset preview focus-ring" aria-label="Edit ${t.name}">
        ${e ? o`<img src=${e} alt="" />` : this._failedThumbs.has(t.id) ? o`<span class="thumb-failed"><ha-icon icon="mdi:image-broken-variant"></ha-icon></span>` : o`<span class="skeleton"></span>`}
      </button>
      <div class="view-info">
        <div class="grow">
          <h3 class="ellipsis">${t.name}</h3>
          <div class="meta ellipsis">${Ht(this._config, t)}</div>
          <div class="meta ellipsis on ${i.length ? "assigned" : ""}">
            ${i.length ? o`<ha-icon icon="mdi:monitor"></ha-icon>${i.length === 1 ? i[0].name : O(i.length, "display")}` : "Not on any display"}
          </div>
        </div>
        <gm-menu
          label="${t.name} actions"
          @click=${(s) => s.stopPropagation()}
          .items=${[
      { key: "edit", label: "Edit", icon: "mdi:pencil" },
      { key: "duplicate", label: "Duplicate", icon: "mdi:content-copy" },
      { key: "delete", label: "Delete", icon: "mdi:delete", danger: !0 }
    ]}
          @action=${(s) => {
      s.detail === "edit" && (this._editing = t), s.detail === "duplicate" && this._duplicate(t), s.detail === "delete" && (this._deleting = t);
    }}
        ></gm-menu>
      </div>
    </ha-card>`;
  }
  _renderCreateDialog() {
    if (!this._createOpen) return d;
    const t = () => {
      this._creating || (this._createOpen = !1);
    };
    return o`<gm-dialog open heading="New view" @cancel=${t}>
      <ha-input
        class="create-view-name"
        label="Name"
        .value=${this._newName}
        @input=${(e) => this._newName = e.target.value}
        @keydown=${(e) => {
      e.key === "Enter" && this._create();
    }}
      ></ha-input>
      ${this._createError ? o`<ha-alert alert-type="error">${this._createError}</ha-alert>` : d}
      <ha-button slot="actions" appearance="plain" ?disabled=${this._creating} @click=${t}>Cancel</ha-button>
      <ha-button
        slot="actions"
        variant="brand"
        appearance="accent"
        ?disabled=${!this._newName.trim() || this._creating}
        .loading=${this._creating}
        @click=${() => this._create()}
        >Create</ha-button
      >
    </gm-dialog>`;
  }
  _renderDeleteDialog() {
    const t = this._deleting;
    if (!t) return d;
    const e = this._devicesShowing(t.id);
    return o`<gm-dialog open heading='Delete "${t.name}"?' @cancel=${() => this._deleting = null}>
      ${e.length ? o`It will be removed from the rotation of ${e.map((i) => i.name).join(", ")}. This can't be undone.` : "This can't be undone."}
      <ha-button slot="actions" appearance="plain" @click=${() => this._deleting = null}>Cancel</ha-button>
      <ha-button slot="actions" variant="danger" appearance="accent" @click=${() => this._delete(t)}>Delete</ha-button>
    </gm-dialog>`;
  }
};
v.styles = [
  re,
  P`
      :host {
        display: flex;
        flex-direction: column;
        /* HA gives custom panels no height: fill the viewport so the toolbar
           stays put and .content is the one scroller. */
        height: 100vh;
        height: 100dvh;
        background: var(--primary-background-color);
        color: var(--primary-text-color);
      }
      gm-view-editor {
        flex: 1;
        min-height: 0;
      }
      .toolbar {
        display: flex;
        align-items: center;
        gap: 4px;
        height: var(--header-height, 56px);
        padding: 0 12px 0 4px;
        flex: none;
        background: var(--app-header-background-color, var(--primary-background-color));
        color: var(--app-header-text-color, var(--primary-text-color));
        border-bottom: var(--app-header-border-bottom, 1px solid var(--divider-color));
      }
      .title {
        font-size: 20px;
        line-height: 28px;
        margin-left: 12px;
      }
      .content {
        flex: 1;
        overflow: auto;
      }
      .page {
        max-width: 1200px;
        margin: 0 auto;
        padding: 24px 24px 104px;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 32px;
      }
      .page.narrow {
        padding: 16px 16px 104px;
        gap: 24px;
      }
      .page.narrow .views {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
      }
      .loading {
        display: flex;
        justify-content: center;
        padding: 96px 0;
      }
      .devices {
        display: grid;
        grid-template-columns: minmax(0, 1fr);
        gap: 16px;
      }
      section {
        min-width: 0;
      }
      .views-head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 8px;
      }
      .views-head ha-button {
        margin-top: -4px;
      }
      .views {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 16px;
      }
      .view-card {
        cursor: pointer;
        overflow: hidden;
        transition: box-shadow 0.15s;
      }
      .view-card:hover {
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12);
      }
      .preview {
        display: block;
        width: 100%;
        aspect-ratio: 1;
        background: #000;
      }
      .preview img,
      .preview .skeleton,
      .thumb-failed {
        display: block;
        width: 100%;
        height: 100%;
      }
      .thumb-failed {
        display: flex;
        align-items: center;
        justify-content: center;
        color: rgba(255, 255, 255, 0.5);
        --mdc-icon-size: 40px;
      }
      .view-info {
        display: flex;
        align-items: flex-start;
        gap: 4px;
        padding: 12px 4px 12px 16px;
        border-top: 1px solid var(--divider-color);
      }
      .view-info h3 {
        font-size: 16px;
        font-weight: 500;
        line-height: 24px;
      }
      .meta {
        font-size: 13px;
        line-height: 18px;
        color: var(--secondary-text-color);
      }
      .on {
        display: flex;
        align-items: center;
        gap: 4px;
        margin-top: 2px;
        --mdc-icon-size: 14px;
      }
      .on.assigned {
        color: var(--primary-color);
      }
      .empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        padding: 48px 24px;
        text-align: center;
        border: 2px dashed var(--divider-color);
        border-radius: var(--gm-radius);
        --mdc-icon-size: 48px;
        color: var(--secondary-text-color);
      }
      .empty h3 {
        color: var(--primary-text-color);
        font-size: 18px;
        font-weight: 500;
      }
      .empty ha-button {
        margin-top: 8px;
      }
      .fab {
        position: fixed;
        right: 24px;
        bottom: 24px;
        z-index: 3;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
        border-radius: 999px;
        --ha-button-border-radius: 999px;
      }
      ha-alert a {
        color: var(--primary-color);
      }
      gm-dialog ha-input {
        display: block;
      }
      gm-dialog ha-alert {
        display: block;
        margin-top: 12px;
      }
    `
];
b([
  m({ attribute: !1 })
], v.prototype, "hass", 2);
b([
  m({ type: Boolean })
], v.prototype, "narrow", 2);
b([
  m({ attribute: !1 })
], v.prototype, "route", 2);
b([
  m({ attribute: !1 })
], v.prototype, "panel", 2);
b([
  u()
], v.prototype, "_config", 2);
b([
  u()
], v.prototype, "_views", 2);
b([
  u()
], v.prototype, "_devices", 2);
b([
  u()
], v.prototype, "_loadError", 2);
b([
  u()
], v.prototype, "_editing", 2);
b([
  u()
], v.prototype, "_thumbs", 2);
b([
  u()
], v.prototype, "_failedThumbs", 2);
b([
  u()
], v.prototype, "_createOpen", 2);
b([
  u()
], v.prototype, "_newName", 2);
b([
  u()
], v.prototype, "_creating", 2);
b([
  u()
], v.prototype, "_createError", 2);
b([
  u()
], v.prototype, "_deleting", 2);
b([
  u()
], v.prototype, "_importOpen", 2);
b([
  u()
], v.prototype, "_width", 2);
v = b([
  N("geekmagic-panel")
], v);
export {
  v as GeekMagicPanel
};
