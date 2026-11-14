/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const se = globalThis, _e = se.ShadowRoot && (se.ShadyCSS === void 0 || se.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, be = Symbol(), xe = /* @__PURE__ */ new WeakMap();
let Ve = class {
  constructor(e, i, s) {
    if (this._$cssResult$ = !0, s !== be) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = e, this.t = i;
  }
  get styleSheet() {
    let e = this.o;
    const i = this.t;
    if (_e && e === void 0) {
      const s = i !== void 0 && i.length === 1;
      s && (e = xe.get(i)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), s && xe.set(i, e));
    }
    return e;
  }
  toString() {
    return this.cssText;
  }
};
const tt = (t) => new Ve(typeof t == "string" ? t : t + "", void 0, be), z = (t, ...e) => {
  const i = t.length === 1 ? t[0] : e.reduce((s, a, r) => s + ((n) => {
    if (n._$cssResult$ === !0) return n.cssText;
    if (typeof n == "number") return n;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + n + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(a) + t[r + 1], t[0]);
  return new Ve(i, t, be);
}, it = (t, e) => {
  if (_e) t.adoptedStyleSheets = e.map((i) => i instanceof CSSStyleSheet ? i : i.styleSheet);
  else for (const i of e) {
    const s = document.createElement("style"), a = se.litNonce;
    a !== void 0 && s.setAttribute("nonce", a), s.textContent = i.cssText, t.appendChild(s);
  }
}, we = _e ? (t) => t : (t) => t instanceof CSSStyleSheet ? ((e) => {
  let i = "";
  for (const s of e.cssRules) i += s.cssText;
  return tt(i);
})(t) : t;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: st, defineProperty: at, getOwnPropertyDescriptor: rt, getOwnPropertyNames: nt, getOwnPropertySymbols: ot, getPrototypeOf: lt } = Object, T = globalThis, ke = T.trustedTypes, ct = ke ? ke.emptyScript : "", de = T.reactiveElementPolyfillSupport, G = (t, e) => t, ae = { toAttribute(t, e) {
  switch (e) {
    case Boolean:
      t = t ? ct : null;
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
} }, ye = (t, e) => !st(t, e), Ae = { attribute: !0, type: String, converter: ae, reflect: !1, useDefault: !1, hasChanged: ye };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), T.litPropertyMetadata ?? (T.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let I = class extends HTMLElement {
  static addInitializer(e) {
    this._$Ei(), (this.l ?? (this.l = [])).push(e);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(e, i = Ae) {
    if (i.state && (i.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((i = Object.create(i)).wrapped = !0), this.elementProperties.set(e, i), !i.noAccessor) {
      const s = Symbol(), a = this.getPropertyDescriptor(e, s, i);
      a !== void 0 && at(this.prototype, e, a);
    }
  }
  static getPropertyDescriptor(e, i, s) {
    const { get: a, set: r } = rt(this.prototype, e) ?? { get() {
      return this[i];
    }, set(n) {
      this[i] = n;
    } };
    return { get: a, set(n) {
      const c = a == null ? void 0 : a.call(this);
      r == null || r.call(this, n), this.requestUpdate(e, c, s);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(e) {
    return this.elementProperties.get(e) ?? Ae;
  }
  static _$Ei() {
    if (this.hasOwnProperty(G("elementProperties"))) return;
    const e = lt(this);
    e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(G("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(G("properties"))) {
      const i = this.properties, s = [...nt(i), ...ot(i)];
      for (const a of s) this.createProperty(a, i[a]);
    }
    const e = this[Symbol.metadata];
    if (e !== null) {
      const i = litPropertyMetadata.get(e);
      if (i !== void 0) for (const [s, a] of i) this.elementProperties.set(s, a);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [i, s] of this.elementProperties) {
      const a = this._$Eu(i, s);
      a !== void 0 && this._$Eh.set(a, i);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(e) {
    const i = [];
    if (Array.isArray(e)) {
      const s = new Set(e.flat(1 / 0).reverse());
      for (const a of s) i.unshift(we(a));
    } else e !== void 0 && i.push(we(e));
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
    return it(e, this.constructor.elementStyles), e;
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
    var r;
    const s = this.constructor.elementProperties.get(e), a = this.constructor._$Eu(e, s);
    if (a !== void 0 && s.reflect === !0) {
      const n = (((r = s.converter) == null ? void 0 : r.toAttribute) !== void 0 ? s.converter : ae).toAttribute(i, s.type);
      this._$Em = e, n == null ? this.removeAttribute(a) : this.setAttribute(a, n), this._$Em = null;
    }
  }
  _$AK(e, i) {
    var r, n;
    const s = this.constructor, a = s._$Eh.get(e);
    if (a !== void 0 && this._$Em !== a) {
      const c = s.getPropertyOptions(a), l = typeof c.converter == "function" ? { fromAttribute: c.converter } : ((r = c.converter) == null ? void 0 : r.fromAttribute) !== void 0 ? c.converter : ae;
      this._$Em = a;
      const d = l.fromAttribute(i, c.type);
      this[a] = d ?? ((n = this._$Ej) == null ? void 0 : n.get(a)) ?? d, this._$Em = null;
    }
  }
  requestUpdate(e, i, s) {
    var a;
    if (e !== void 0) {
      const r = this.constructor, n = this[e];
      if (s ?? (s = r.getPropertyOptions(e)), !((s.hasChanged ?? ye)(n, i) || s.useDefault && s.reflect && n === ((a = this._$Ej) == null ? void 0 : a.get(e)) && !this.hasAttribute(r._$Eu(e, s)))) return;
      this.C(e, i, s);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(e, i, { useDefault: s, reflect: a, wrapped: r }, n) {
    s && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(e) && (this._$Ej.set(e, n ?? i ?? this[e]), r !== !0 || n !== void 0) || (this._$AL.has(e) || (this.hasUpdated || s || (i = void 0), this._$AL.set(e, i)), a === !0 && this._$Em !== e && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(e));
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
        for (const [r, n] of this._$Ep) this[r] = n;
        this._$Ep = void 0;
      }
      const a = this.constructor.elementProperties;
      if (a.size > 0) for (const [r, n] of a) {
        const { wrapped: c } = n, l = this[r];
        c !== !0 || this._$AL.has(r) || l === void 0 || this.C(r, void 0, n, l);
      }
    }
    let e = !1;
    const i = this._$AL;
    try {
      e = this.shouldUpdate(i), e ? (this.willUpdate(i), (s = this._$EO) == null || s.forEach((a) => {
        var r;
        return (r = a.hostUpdate) == null ? void 0 : r.call(a);
      }), this.update(i)) : this._$EM();
    } catch (a) {
      throw e = !1, this._$EM(), a;
    }
    e && this._$AE(i);
  }
  willUpdate(e) {
  }
  _$AE(e) {
    var i;
    (i = this._$EO) == null || i.forEach((s) => {
      var a;
      return (a = s.hostUpdated) == null ? void 0 : a.call(s);
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
I.elementStyles = [], I.shadowRootOptions = { mode: "open" }, I[G("elementProperties")] = /* @__PURE__ */ new Map(), I[G("finalized")] = /* @__PURE__ */ new Map(), de == null || de({ ReactiveElement: I }), (T.reactiveElementVersions ?? (T.reactiveElementVersions = [])).push("2.1.1");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Z = globalThis, re = Z.trustedTypes, Se = re ? re.createPolicy("lit-html", { createHTML: (t) => t }) : void 0, qe = "$lit$", C = `lit$${Math.random().toFixed(9).slice(2)}$`, Be = "?" + C, dt = `<${Be}>`, R = document, K = () => R.createComment(""), J = (t) => t === null || typeof t != "object" && typeof t != "function", $e = Array.isArray, ht = (t) => $e(t) || typeof (t == null ? void 0 : t[Symbol.iterator]) == "function", he = `[ 	
\f\r]`, W = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, Ee = /-->/g, Ce = />/g, M = RegExp(`>|${he}(?:([^\\s"'>=/]+)(${he}*=${he}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), Te = /'/g, ze = /"/g, Fe = /^(?:script|style|textarea|title)$/i, We = (t) => (e, ...i) => ({ _$litType$: t, strings: e, values: i }), o = We(1), pt = We(2), q = Symbol.for("lit-noChange"), h = Symbol.for("lit-nothing"), Oe = /* @__PURE__ */ new WeakMap(), P = R.createTreeWalker(R, 129);
function Ge(t, e) {
  if (!$e(t) || !t.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return Se !== void 0 ? Se.createHTML(e) : e;
}
const ut = (t, e) => {
  const i = t.length - 1, s = [];
  let a, r = e === 2 ? "<svg>" : e === 3 ? "<math>" : "", n = W;
  for (let c = 0; c < i; c++) {
    const l = t[c];
    let d, p, u = -1, _ = 0;
    for (; _ < l.length && (n.lastIndex = _, p = n.exec(l), p !== null); ) _ = n.lastIndex, n === W ? p[1] === "!--" ? n = Ee : p[1] !== void 0 ? n = Ce : p[2] !== void 0 ? (Fe.test(p[2]) && (a = RegExp("</" + p[2], "g")), n = M) : p[3] !== void 0 && (n = M) : n === M ? p[0] === ">" ? (n = a ?? W, u = -1) : p[1] === void 0 ? u = -2 : (u = n.lastIndex - p[2].length, d = p[1], n = p[3] === void 0 ? M : p[3] === '"' ? ze : Te) : n === ze || n === Te ? n = M : n === Ee || n === Ce ? n = W : (n = M, a = void 0);
    const x = n === M && t[c + 1].startsWith("/>") ? " " : "";
    r += n === W ? l + dt : u >= 0 ? (s.push(d), l.slice(0, u) + qe + l.slice(u) + C + x) : l + C + (u === -2 ? c : x);
  }
  return [Ge(t, r + (t[i] || "<?>") + (e === 2 ? "</svg>" : e === 3 ? "</math>" : "")), s];
};
class Y {
  constructor({ strings: e, _$litType$: i }, s) {
    let a;
    this.parts = [];
    let r = 0, n = 0;
    const c = e.length - 1, l = this.parts, [d, p] = ut(e, i);
    if (this.el = Y.createElement(d, s), P.currentNode = this.el.content, i === 2 || i === 3) {
      const u = this.el.content.firstChild;
      u.replaceWith(...u.childNodes);
    }
    for (; (a = P.nextNode()) !== null && l.length < c; ) {
      if (a.nodeType === 1) {
        if (a.hasAttributes()) for (const u of a.getAttributeNames()) if (u.endsWith(qe)) {
          const _ = p[n++], x = a.getAttribute(u).split(C), O = /([.?@])?(.*)/.exec(_);
          l.push({ type: 1, index: r, name: O[2], strings: x, ctor: O[1] === "." ? mt : O[1] === "?" ? vt : O[1] === "@" ? ft : oe }), a.removeAttribute(u);
        } else u.startsWith(C) && (l.push({ type: 6, index: r }), a.removeAttribute(u));
        if (Fe.test(a.tagName)) {
          const u = a.textContent.split(C), _ = u.length - 1;
          if (_ > 0) {
            a.textContent = re ? re.emptyScript : "";
            for (let x = 0; x < _; x++) a.append(u[x], K()), P.nextNode(), l.push({ type: 2, index: ++r });
            a.append(u[_], K());
          }
        }
      } else if (a.nodeType === 8) if (a.data === Be) l.push({ type: 2, index: r });
      else {
        let u = -1;
        for (; (u = a.data.indexOf(C, u + 1)) !== -1; ) l.push({ type: 7, index: r }), u += C.length - 1;
      }
      r++;
    }
  }
  static createElement(e, i) {
    const s = R.createElement("template");
    return s.innerHTML = e, s;
  }
}
function B(t, e, i = t, s) {
  var n, c;
  if (e === q) return e;
  let a = s !== void 0 ? (n = i._$Co) == null ? void 0 : n[s] : i._$Cl;
  const r = J(e) ? void 0 : e._$litDirective$;
  return (a == null ? void 0 : a.constructor) !== r && ((c = a == null ? void 0 : a._$AO) == null || c.call(a, !1), r === void 0 ? a = void 0 : (a = new r(t), a._$AT(t, i, s)), s !== void 0 ? (i._$Co ?? (i._$Co = []))[s] = a : i._$Cl = a), a !== void 0 && (e = B(t, a._$AS(t, e.values), a, s)), e;
}
class gt {
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
    const { el: { content: i }, parts: s } = this._$AD, a = ((e == null ? void 0 : e.creationScope) ?? R).importNode(i, !0);
    P.currentNode = a;
    let r = P.nextNode(), n = 0, c = 0, l = s[0];
    for (; l !== void 0; ) {
      if (n === l.index) {
        let d;
        l.type === 2 ? d = new X(r, r.nextSibling, this, e) : l.type === 1 ? d = new l.ctor(r, l.name, l.strings, this, e) : l.type === 6 && (d = new _t(r, this, e)), this._$AV.push(d), l = s[++c];
      }
      n !== (l == null ? void 0 : l.index) && (r = P.nextNode(), n++);
    }
    return P.currentNode = R, a;
  }
  p(e) {
    let i = 0;
    for (const s of this._$AV) s !== void 0 && (s.strings !== void 0 ? (s._$AI(e, s, i), i += s.strings.length - 2) : s._$AI(e[i])), i++;
  }
}
class X {
  get _$AU() {
    var e;
    return ((e = this._$AM) == null ? void 0 : e._$AU) ?? this._$Cv;
  }
  constructor(e, i, s, a) {
    this.type = 2, this._$AH = h, this._$AN = void 0, this._$AA = e, this._$AB = i, this._$AM = s, this.options = a, this._$Cv = (a == null ? void 0 : a.isConnected) ?? !0;
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
    e = B(this, e, i), J(e) ? e === h || e == null || e === "" ? (this._$AH !== h && this._$AR(), this._$AH = h) : e !== this._$AH && e !== q && this._(e) : e._$litType$ !== void 0 ? this.$(e) : e.nodeType !== void 0 ? this.T(e) : ht(e) ? this.k(e) : this._(e);
  }
  O(e) {
    return this._$AA.parentNode.insertBefore(e, this._$AB);
  }
  T(e) {
    this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
  }
  _(e) {
    this._$AH !== h && J(this._$AH) ? this._$AA.nextSibling.data = e : this.T(R.createTextNode(e)), this._$AH = e;
  }
  $(e) {
    var r;
    const { values: i, _$litType$: s } = e, a = typeof s == "number" ? this._$AC(e) : (s.el === void 0 && (s.el = Y.createElement(Ge(s.h, s.h[0]), this.options)), s);
    if (((r = this._$AH) == null ? void 0 : r._$AD) === a) this._$AH.p(i);
    else {
      const n = new gt(a, this), c = n.u(this.options);
      n.p(i), this.T(c), this._$AH = n;
    }
  }
  _$AC(e) {
    let i = Oe.get(e.strings);
    return i === void 0 && Oe.set(e.strings, i = new Y(e)), i;
  }
  k(e) {
    $e(this._$AH) || (this._$AH = [], this._$AR());
    const i = this._$AH;
    let s, a = 0;
    for (const r of e) a === i.length ? i.push(s = new X(this.O(K()), this.O(K()), this, this.options)) : s = i[a], s._$AI(r), a++;
    a < i.length && (this._$AR(s && s._$AB.nextSibling, a), i.length = a);
  }
  _$AR(e = this._$AA.nextSibling, i) {
    var s;
    for ((s = this._$AP) == null ? void 0 : s.call(this, !1, !0, i); e !== this._$AB; ) {
      const a = e.nextSibling;
      e.remove(), e = a;
    }
  }
  setConnected(e) {
    var i;
    this._$AM === void 0 && (this._$Cv = e, (i = this._$AP) == null || i.call(this, e));
  }
}
class oe {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(e, i, s, a, r) {
    this.type = 1, this._$AH = h, this._$AN = void 0, this.element = e, this.name = i, this._$AM = a, this.options = r, s.length > 2 || s[0] !== "" || s[1] !== "" ? (this._$AH = Array(s.length - 1).fill(new String()), this.strings = s) : this._$AH = h;
  }
  _$AI(e, i = this, s, a) {
    const r = this.strings;
    let n = !1;
    if (r === void 0) e = B(this, e, i, 0), n = !J(e) || e !== this._$AH && e !== q, n && (this._$AH = e);
    else {
      const c = e;
      let l, d;
      for (e = r[0], l = 0; l < r.length - 1; l++) d = B(this, c[s + l], i, l), d === q && (d = this._$AH[l]), n || (n = !J(d) || d !== this._$AH[l]), d === h ? e = h : e !== h && (e += (d ?? "") + r[l + 1]), this._$AH[l] = d;
    }
    n && !a && this.j(e);
  }
  j(e) {
    e === h ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
  }
}
class mt extends oe {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(e) {
    this.element[this.name] = e === h ? void 0 : e;
  }
}
class vt extends oe {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(e) {
    this.element.toggleAttribute(this.name, !!e && e !== h);
  }
}
class ft extends oe {
  constructor(e, i, s, a, r) {
    super(e, i, s, a, r), this.type = 5;
  }
  _$AI(e, i = this) {
    if ((e = B(this, e, i, 0) ?? h) === q) return;
    const s = this._$AH, a = e === h && s !== h || e.capture !== s.capture || e.once !== s.once || e.passive !== s.passive, r = e !== h && (s === h || a);
    a && this.element.removeEventListener(this.name, this, s), r && this.element.addEventListener(this.name, this, e), this._$AH = e;
  }
  handleEvent(e) {
    var i;
    typeof this._$AH == "function" ? this._$AH.call(((i = this.options) == null ? void 0 : i.host) ?? this.element, e) : this._$AH.handleEvent(e);
  }
}
class _t {
  constructor(e, i, s) {
    this.element = e, this.type = 6, this._$AN = void 0, this._$AM = i, this.options = s;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(e) {
    B(this, e);
  }
}
const pe = Z.litHtmlPolyfillSupport;
pe == null || pe(Y, X), (Z.litHtmlVersions ?? (Z.litHtmlVersions = [])).push("3.3.1");
const bt = (t, e, i) => {
  const s = (i == null ? void 0 : i.renderBefore) ?? e;
  let a = s._$litPart$;
  if (a === void 0) {
    const r = (i == null ? void 0 : i.renderBefore) ?? null;
    s._$litPart$ = a = new X(e.insertBefore(K(), r), r, void 0, i ?? {});
  }
  return a._$AI(t), a;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const L = globalThis;
class k extends I {
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
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = bt(i, this.renderRoot, this.renderOptions);
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
    return q;
  }
}
var Ie;
k._$litElement$ = !0, k.finalized = !0, (Ie = L.litElementHydrateSupport) == null || Ie.call(L, { LitElement: k });
const ue = L.litElementPolyfillSupport;
ue == null || ue({ LitElement: k });
(L.litElementVersions ?? (L.litElementVersions = [])).push("4.2.1");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const H = (t) => (e, i) => {
  i !== void 0 ? i.addInitializer(() => {
    customElements.define(t, e);
  }) : customElements.define(t, e);
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const yt = { attribute: !0, type: String, converter: ae, reflect: !1, hasChanged: ye }, $t = (t = yt, e, i) => {
  const { kind: s, metadata: a } = i;
  let r = globalThis.litPropertyMetadata.get(a);
  if (r === void 0 && globalThis.litPropertyMetadata.set(a, r = /* @__PURE__ */ new Map()), s === "setter" && ((t = Object.create(t)).wrapped = !0), r.set(i.name, t), s === "accessor") {
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
  return (e, i) => typeof i == "object" ? $t(t, e, i) : ((s, a, r) => {
    const n = a.hasOwnProperty(r);
    return a.constructor.createProperty(r, s), n ? Object.getOwnPropertyDescriptor(a, r) : void 0;
  })(t, e, i);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function g(t) {
  return m({ ...t, state: !0, attribute: !1 });
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const xt = (t, e, i) => (i.configurable = !0, i.enumerable = !0, Reflect.decorate && typeof e != "object" && Object.defineProperty(t, e, i), i);
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function wt(t, e) {
  return (i, s, a) => {
    const r = (n) => {
      var c;
      return ((c = n.renderRoot) == null ? void 0 : c.querySelector(t)) ?? null;
    };
    return xt(i, s, { get() {
      return r(this);
    } });
  };
}
class kt {
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
async function me(t, e, i) {
  const s = [...t], a = Array.from({ length: Math.min(e, s.length) }, async () => {
    for (; s.length; ) await i(s.shift());
  });
  await Promise.all(a);
}
const ne = (t) => `data:image/png;base64,${t}`;
class At {
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
function Me(t) {
  return JSON.parse(JSON.stringify(t));
}
function V(t, e) {
  return t.widgets.find((i) => i.slot === e);
}
function ve(t, e, i) {
  const a = V(t, e) ? t.widgets.map((r) => r.slot === e ? { ...r, ...i, slot: e } : r) : [...t.widgets, { type: "", ...i, slot: e }];
  return { ...t, widgets: a };
}
function St(t, e, i, s = {}) {
  const a = V(t, e), r = { slot: e, type: i, options: { ...s } };
  a != null && a.entity_id && (r.entity_id = a.entity_id), a != null && a.label && (r.label = a.label);
  const n = a ? t.widgets.map((c) => c.slot === e ? r : c) : [...t.widgets, r];
  return { ...t, widgets: n };
}
function Et(t, e, i, s) {
  const a = V(t, e), r = { ...(a == null ? void 0 : a.options) ?? {} };
  return s === void 0 ? delete r[i] : r[i] = s, ve(t, e, { options: r });
}
function Pe(t, e, i) {
  if (e === i) return t;
  const s = t.widgets.map(
    (a) => a.slot === e ? { ...a, slot: i } : a.slot === i ? { ...a, slot: e } : a
  );
  return { ...t, widgets: s };
}
function Ct(t, e) {
  return { ...t, widgets: t.widgets.filter((i) => i.slot !== e) };
}
function Tt(t, e) {
  return t.widgets.filter((i) => i.slot >= e && i.type);
}
function zt(t, e) {
  return { ...t, widgets: t.widgets.filter((i) => i.slot < e) };
}
function Ot(t, e) {
  return t.widgets.filter((i) => i.type && i.slot < e).length;
}
function N(t, e, i = `${e}s`) {
  return `${t} ${t === 1 ? e : i}`;
}
function fe(t, e) {
  var i;
  return ((i = t == null ? void 0 : t.layout_types[e]) == null ? void 0 : i.slots) ?? 4;
}
function Mt(t, e) {
  var r;
  const i = ((r = t == null ? void 0 : t.layout_types[e.layout]) == null ? void 0 : r.name) ?? e.layout, s = (t == null ? void 0 : t.themes[e.theme]) ?? e.theme, a = Ot(e, fe(t, e.layout));
  return `${i} · ${s} · ${N(a, "widget")}`;
}
function Pt(t, e, i) {
  return t.label ? t.label : t.entity_id ? e(t.entity_id) ?? t.entity_id : i;
}
function Lt(t) {
  const e = [5, 10, 15, 30, 60, 120, 300];
  return (e.includes(t) || t <= 0 ? e : [...e, t].sort((s, a) => s - a)).map((s) => ({ value: s, label: Ze(s) }));
}
function Ze(t) {
  return t < 60 ? `${t} s` : t % 60 === 0 ? `${t / 60} min` : `${Math.floor(t / 60)} min ${t % 60} s`;
}
function Nt(t, e) {
  if (!t) return null;
  const i = t.includes("?") ? "&" : "?";
  return e ? `${t}${i}v=${encodeURIComponent(e)}` : t;
}
function Rt(t, e = "New view") {
  const i = new Set(t.map((a) => a.name));
  if (!i.has(e)) return e;
  let s = 2;
  for (; i.has(`${e} ${s}`); ) s += 1;
  return `${e} ${s}`;
}
const le = z`
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
`, Le = {
  values: "#0a84ff",
  home: "#30a14e",
  time: "#ff9f0a",
  history: "#8e5cf6",
  pictures: "#e0436b",
  custom: "#5f6b7a"
}, Dt = {
  values: "Values",
  home: "Home",
  time: "Time & weather",
  history: "History",
  pictures: "Pictures",
  custom: "Custom"
}, $ = {
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
function Ut(t, e = 1500) {
  const s = 6e4 - t % 6e4 + e;
  return s > 6e4 ? s - 6e4 : s;
}
function Ke(t, e = 1500) {
  let i;
  const s = () => {
    i = setTimeout(() => {
      s(), t();
    }, Ut(Date.now(), e));
  };
  return s(), () => clearTimeout(i);
}
const Ne = "Settings → Devices & services";
function Je(t) {
  const e = t.state ?? "loaded";
  return e === "loaded" ? t.online ? { kind: "online", live: !0, label: "Online" } : { kind: "offline", live: !0, label: "Offline" } : t.disabled ? {
    kind: "disabled",
    live: !1,
    label: "Disabled",
    title: "This display is disabled",
    hint: `Enable it in ${Ne} to show your views on it again.`,
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
    hint: `Check the Home Assistant logs, then reload it from ${Ne}.`,
    alert: "error"
  };
}
function Ht(t) {
  return t.some((e) => {
    const i = Je(e).kind;
    return i === "retrying" || i === "starting";
  });
}
function Q(t, e, i) {
  const s = e + i;
  if (e < 0 || e >= t.length || s < 0 || s >= t.length)
    return t;
  const a = [...t], [r] = a.splice(e, 1);
  return a.splice(s, 0, r), a;
}
function jt(t, e, i) {
  return Q(t, e, i - e);
}
function It(t, e) {
  return [...t, ...e.filter((i) => !t.includes(i))];
}
function Vt(t, e) {
  return t.filter((i) => i !== e);
}
function Re(t, e, i) {
  if (t.length === 0) return null;
  const s = e ? t.indexOf(e) : -1;
  return s < 0 ? t[i === 1 ? 0 : t.length - 1] : t[(s + i + t.length) % t.length];
}
function Ye(t, e) {
  if (t.value !== void 0 && t.value !== null)
    return t.value;
  if (t.index !== void 0 && t.index !== null)
    return e[t.index];
}
var qt = Object.defineProperty, Bt = Object.getOwnPropertyDescriptor, ce = (t, e, i, s) => {
  for (var a = s > 1 ? void 0 : s ? Bt(e, i) : e, r = t.length - 1, n; r >= 0; r--)
    (n = t[r]) && (a = (s ? n(e, i, a) : n(a)) || a);
  return s && a && qt(e, i, a), a;
};
let F = class extends k {
  constructor() {
    super(...arguments), this.heading = "", this.open = !1;
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
F.styles = z`
    dialog {
      padding: 0;
      border: 0;
      border-radius: 28px;
      background: var(--ha-dialog-surface-background, var(--card-background-color));
      color: var(--primary-text-color);
      width: min(440px, calc(100vw - 32px));
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
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
ce([
  m()
], F.prototype, "heading", 2);
ce([
  m({ type: Boolean, reflect: !0 })
], F.prototype, "open", 2);
ce([
  wt("dialog")
], F.prototype, "_dialog", 2);
F = ce([
  H("gm-dialog")
], F);
var Ft = Object.defineProperty, Wt = Object.getOwnPropertyDescriptor, ee = (t, e, i, s) => {
  for (var a = s > 1 ? void 0 : s ? Wt(e, i) : e, r = t.length - 1, n; r >= 0; r--)
    (n = t[r]) && (a = (s ? n(e, i, a) : n(a)) || a);
  return s && a && Ft(e, i, a), a;
};
let D = class extends k {
  constructor() {
    super(...arguments), this.items = [], this.label = "More actions", this._open = !1, this._at = { top: 0, right: 0 }, this._outside = (t) => {
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
    t.has("_open") && this._open && ((e = this.renderRoot.querySelector("[role=menuitem]:not([disabled])")) == null || e.focus());
  }
  _toggle(t) {
    if (t.stopPropagation(), !this._open) {
      const e = this.getBoundingClientRect();
      this._at = { top: e.bottom, right: Math.max(8, window.innerWidth - e.right) };
    }
    this._open = !this._open;
  }
  _pick(t, e) {
    t.stopPropagation(), !e.disabled && (this._open = !1, this.dispatchEvent(new CustomEvent("action", { detail: e.key })));
  }
  render() {
    return o`
      <ha-icon-button
        .path=${$.dots}
        .label=${this.label}
        aria-haspopup="menu"
        aria-expanded=${this._open ? "true" : "false"}
        @click=${this._toggle}
      ></ha-icon-button>
      ${this._open ? o`<div
            class="menu"
            role="menu"
            style="top:${this._at.top}px;right:${this._at.right}px"
            @click=${(t) => t.stopPropagation()}
          >
            ${this.items.map(
      (t) => o`<button
                role="menuitem"
                class=${t.danger ? "danger" : ""}
                ?disabled=${t.disabled}
                @click=${(e) => this._pick(e, t)}
              >
                ${t.icon ? o`<ha-icon .icon=${t.icon}></ha-icon>` : h}
                <span>${t.label}</span>
              </button>`
    )}
          </div>` : h}
    `;
  }
};
D.styles = z`
    :host {
      position: relative;
      display: inline-block;
    }
    .menu {
      position: fixed;
      z-index: 10;
      max-height: 60vh;
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
ee([
  m({ attribute: !1 })
], D.prototype, "items", 2);
ee([
  m()
], D.prototype, "label", 2);
ee([
  g()
], D.prototype, "_open", 2);
ee([
  g()
], D.prototype, "_at", 2);
D = ee([
  H("gm-menu")
], D);
var Gt = Object.defineProperty, Zt = Object.getOwnPropertyDescriptor, j = (t, e, i, s) => {
  for (var a = s > 1 ? void 0 : s ? Zt(e, i) : e, r = t.length - 1, n; r >= 0; r--)
    (n = t[r]) && (a = (s ? n(e, i, a) : n(a)) || a);
  return s && a && Gt(e, i, a), a;
};
let E = class extends k {
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
          ${this.busy ? o`<div class="progress"></div>` : h}
        </div>
      </div>
    `;
  }
};
E.styles = z`
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
j([
  m()
], E.prototype, "src", 2);
j([
  m()
], E.prototype, "alt", 2);
j([
  m({ type: Number })
], E.prototype, "size", 2);
j([
  m({ attribute: "img-class" })
], E.prototype, "imgClass", 2);
j([
  m({ type: Boolean, reflect: !0 })
], E.prototype, "busy", 2);
j([
  m({ type: Boolean, reflect: !0 })
], E.prototype, "dim", 2);
E = j([
  H("gm-screen")
], E);
var Kt = Object.defineProperty, Jt = Object.getOwnPropertyDescriptor, A = (t, e, i, s) => {
  for (var a = s > 1 ? void 0 : s ? Jt(e, i) : e, r = t.length - 1, n; r >= 0; r--)
    (n = t[r]) && (a = (s ? n(e, i, a) : n(a)) || a);
  return s && a && Kt(e, i, a), a;
};
let w = class extends k {
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
    } catch (a) {
      this._notify(`Couldn't ${s}: ${S(a)}`);
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
        this._setRotation(Q(this._rotation, e, -1), "reorder the rotation");
        break;
      case "later":
        this._setRotation(Q(this._rotation, e, 1), "reorder the rotation");
        break;
      case "remove":
        this._setRotation(Vt(this._rotation, t), "remove the view");
        break;
    }
  }
  // ---- render --------------------------------------------------------------------
  render() {
    const t = this.device, e = Je(t), i = this._state("preview"), s = this._state("active"), a = (s == null ? void 0 : s.state) === "off", r = t.display_mode === "builtin", n = i && i.state !== "unavailable" ? Nt(i.attributes.entity_picture, i.state) : null, c = n && this.hass.hassUrl ? this.hass.hassUrl(n) : n, l = this.views.find((d) => d.id === t.current_view_id);
    return o`
      <ha-card outlined>
        <div class="top ${this.narrow ? "narrow" : ""}">
          <gm-screen
            .src=${c}
            .size=${this.narrow ? 200 : 184}
            alt="${t.name}'s screen"
            ?dim=${!t.online || a}
          >
            <div slot="empty" class="screen-empty">
              ${t.online ? o`<ha-spinner size="s"></ha-spinner><span>Waiting for the first frame</span>` : o`<ha-icon icon=${e.kind === "disabled" ? "mdi:monitor-off" : "mdi:lan-disconnect"}></ha-icon
                    ><span>${e.label}</span>`}
            </div>
            ${a ? o`<div class="screen-badge"><ha-icon icon="mdi:pause"></ha-icon></div>` : h}
          </gm-screen>
          <div class="info">
            <div class="name-row">
              <h2 class="ellipsis">${t.name}</h2>
              <span class="status ${e.kind}">
                <span class="led"></span>${e.label}
              </span>
            </div>
            <a class="host" href="http://${t.host}" target="_blank" rel="noopener noreferrer">${t.host}</a>

            ${e.live ? t.online ? a ? o`<div class="now">
                    <span class="now-label">Paused</span>
                    <ha-button size="s" appearance="filled" @click=${() => this._service("switch", "turn_on", { entity_id: s.entity_id }, "resume")}>Resume</ha-button>
                  </div>` : r ? o`<div class="now">
                      <ha-icon icon="mdi:television-classic"></ha-icon>
                      <span class="now-label">Built-in: <strong>${t.builtin_mode ?? "firmware screen"}</strong></span>
                      ${this._rotation.length ? o`<ha-button size="s" appearance="filled" @click=${() => this._show(this._rotation[0])}>Show my views</ha-button>` : h}
                    </div>` : o`<div class="now">
                      <span class="now-label">Now showing</span>
                      <strong class="ellipsis now-view">${(l == null ? void 0 : l.name) ?? (this._rotation.length ? "—" : "Welcome screen")}</strong>
                      ${this._rotation.length > 1 ? o`<span class="stepper">
                            <ha-icon-button .path=${$.prev} label="Previous view" @click=${() => this._show(Re(this._rotation, t.current_view_id ?? null, -1))}></ha-icon-button>
                            <ha-icon-button .path=${$.next} label="Next view" @click=${() => this._show(Re(this._rotation, t.current_view_id ?? null, 1))}></ha-icon-button>
                          </span>` : h}
                    </div>` : o`<ha-alert alert-type="warning">Can't reach the display at ${t.host}.</ha-alert>` : this._renderNotLoaded(e)}
            ${e.live ? this._renderControls(!t.online) : h}
          </div>
        </div>
        ${this._renderRotation(e.live)}
      </ha-card>
      ${this._addOpen ? this._renderAddDialog() : h}
    `;
  }
  _renderNotLoaded(t) {
    const e = this.device.reason;
    return o`<ha-alert class="not-loaded" alert-type=${t.alert ?? "warning"} title=${t.title ?? ""}>
      ${e ? o`<div class="reason">${e}</div>` : h}
      ${t.hint ? o`<div>${t.hint}</div>` : h}
    </ha-alert>`;
  }
  _renderControls(t) {
    const e = this._state("brightness"), i = this._state("view_cycling"), s = this._state("cycle_interval"), a = this._brightness ?? Number((e == null ? void 0 : e.state) ?? NaN), r = Number((s == null ? void 0 : s.state) ?? NaN), n = Lt(Number.isFinite(r) ? r : 30);
    return o`<div class="controls">
      ${e && Number.isFinite(a) ? o`<div class="control">
            <ha-icon icon="mdi:brightness-6" title="Brightness"></ha-icon>
            <ha-slider
              class="grow"
              min="0"
              max="100"
              step="1"
              .value=${a}
              ?disabled=${t}
              aria-label="Brightness"
              @input=${(c) => this._brightness = Number(c.target.value)}
              @change=${async (c) => {
      const l = Number(c.target.value);
      await this._service("number", "set_value", { entity_id: e.entity_id, value: l }, "set the brightness"), this._brightness = null;
    }}
            ></ha-slider>
            <span class="value">${Math.round(a)}%</span>
          </div>` : h}
      ${i && this._rotation.length > 1 ? o`<div class="control">
            <ha-icon icon="mdi:rotate-right" title="Rotate views"></ha-icon>
            <label class="grow switch-label" for="cycle-${this.device.entry_id}">Rotate views</label>
            ${i.state === "on" && s && Number.isFinite(r) ? o`<ha-select
                  class="interval"
                  label="Every"
                  .value=${String(r)}
                  .options=${n.map((c) => ({ value: String(c.value), label: c.label }))}
                  ?disabled=${t}
                  @selected=${(c) => {
      const l = Ye(c.detail, n.map((d) => String(d.value)));
      l && Number(l) !== r && this._service("number", "set_value", { entity_id: s.entity_id, value: Number(l) }, "change the interval");
    }}
                  @closed=${(c) => c.stopPropagation()}
                >
                  ${n.map((c) => o`<mwc-list-item value=${String(c.value)}>${c.label}</mwc-list-item>`)}
                </ha-select>` : h}
            <ha-switch
              id="cycle-${this.device.entry_id}"
              .checked=${i.state === "on"}
              ?disabled=${t}
              @change=${(c) => this._service("switch", c.target.checked ? "turn_on" : "turn_off", { entity_id: i.entity_id }, "change rotation")}
            ></ha-switch>
          </div>` : h}
    </div>`;
  }
  /** ``live``: the display runs, so a view can be shown now. */
  _renderRotation(t) {
    var n, c;
    const e = new Map(this.views.map((l) => [l.id, l])), i = this._rotation.filter((l) => e.has(l)), s = ((n = this._state("view_cycling")) == null ? void 0 : n.state) === "on", a = this.views.filter((l) => !this._rotation.includes(l.id)), r = this.device.display_mode === "builtin" ? null : this.device.current_view_id;
    return o`<div class="rotation">
      <div class="rotation-head">
        <span class="caption">Rotation</span>
        <span class="muted">${N(i.length, "view")}</span>
        ${t ? i.length > 1 && !s ? o`<span class="muted hint">Rotation is off: tap a view to show it.</span>` : i.length > 1 ? o`<span class="muted hint">Every ${Ze(Number(((c = this._state("cycle_interval")) == null ? void 0 : c.state) ?? 0))}</span>` : h : o`<span class="muted hint">Changes apply once the display is back.</span>`}
      </div>
      <div class="strip-row">
        <ha-sortable
          draggable-selector=".thumb"
          .disabled=${this.narrow}
          @item-moved=${(l) => {
      l.stopPropagation(), this._setRotation(jt(i, l.detail.oldIndex, l.detail.newIndex), "reorder the rotation");
    }}
        >
          <div class="strip" role="list">
            ${i.map((l, d) => {
      const p = e.get(l), u = l === r;
      return o`<div class="thumb ${u ? "current" : ""}" role="listitem" data-view-id=${l}>
                <button
                  class="reset thumb-button focus-ring"
                  aria-current=${u ? "true" : "false"}
                  aria-label=${t ? `Show ${p.name} now` : p.name}
                  title=${u ? `${p.name} (on screen)` : t ? `Show ${p.name} now` : p.name}
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
        { key: "show", label: "Show now", icon: "mdi:monitor-eye", disabled: u || !t },
        { key: "edit", label: "Edit view", icon: "mdi:pencil" },
        { key: "earlier", label: "Move earlier", icon: "mdi:arrow-left", disabled: d === 0 },
        { key: "later", label: "Move later", icon: "mdi:arrow-right", disabled: d === i.length - 1 },
        { key: "remove", label: "Remove from rotation", icon: "mdi:playlist-remove", danger: !0 }
      ]}
                  @action=${(_) => this._thumbAction(l, this._rotation.indexOf(l), _.detail)}
                ></gm-menu>
              </div>`;
    })}
          </div>
        </ha-sortable>
        ${a.length || !i.length ? o`<button
              class="reset add-thumb focus-ring ${i.length ? "" : "wide"}"
              @click=${() => {
      this._adding = /* @__PURE__ */ new Set(), this._addOpen = !0;
    }}
              ?disabled=${!a.length}
            >
              <ha-svg-icon .path=${$.plus}></ha-svg-icon>
              <span>${i.length ? "Add" : "Add views to show on this display"}</span>
              ${i.length ? h : o`<span class="muted">Until then it shows the welcome screen.</span>`}
            </button>` : h}
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
      this._setRotation(It(this._rotation, i), "add the views");
    }}
        >Add ${this._adding.size ? N(this._adding.size, "view") : ""}</ha-button
      >
    </gm-dialog>`;
  }
};
w.styles = [
  le,
  z`
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
A([
  m({ attribute: !1 })
], w.prototype, "hass", 2);
A([
  m({ attribute: !1 })
], w.prototype, "api", 2);
A([
  m({ attribute: !1 })
], w.prototype, "device", 2);
A([
  m({ attribute: !1 })
], w.prototype, "views", 2);
A([
  m({ attribute: !1 })
], w.prototype, "thumbs", 2);
A([
  m({ type: Boolean })
], w.prototype, "narrow", 2);
A([
  g()
], w.prototype, "_rotation", 2);
A([
  g()
], w.prototype, "_addOpen", 2);
A([
  g()
], w.prototype, "_adding", 2);
A([
  g()
], w.prototype, "_brightness", 2);
w = A([
  H("gm-device-card")
], w);
const Yt = {
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
}, Qt = {
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
}, Qe = {
  sizes: Yt,
  samples: Qt
}, Xe = Qe.sizes, Xt = Qe.samples;
function De(t, e) {
  return [t < 100, e < 100, Math.min(t, e) < 130];
}
function et(t, e) {
  const i = De(t, e);
  let s = "", a = 1 / 0;
  for (const [r, [n, c]] of Object.entries(Xe)) {
    const d = De(n, c).filter((p, u) => p !== i[u]).length * 10 + Math.abs(Math.log(t / n)) + Math.abs(Math.log(e / c));
    d < a && (s = r, a = d);
  }
  return s;
}
function ei(t, e, i, s, a) {
  const r = Xt[i];
  return !r || !(s > 0) || !(a > 0) ? null : `${t}/${r}_${et(s, a)}.png?v=${encodeURIComponent(e)}`;
}
function ti(t) {
  return Xe[t];
}
function ii(t) {
  if (!t || t.length !== 3) return "#000000";
  const [e, i, s] = t;
  return `#${[e, i, s].map((a) => Math.max(0, Math.min(255, a)).toString(16).padStart(2, "0")).join("")}`;
}
function Ue(t) {
  const e = t.trim();
  if (!e) return null;
  const i = e.match(/^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/);
  if (i) {
    let r = i[1];
    return r.length === 3 && (r = r[0] + r[0] + r[1] + r[1] + r[2] + r[2]), [
      parseInt(r.slice(0, 2), 16),
      parseInt(r.slice(2, 4), 16),
      parseInt(r.slice(4, 6), 16)
    ];
  }
  const s = e.match(/^(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})$/);
  if (s) {
    const r = Math.min(255, parseInt(s[1], 10)), n = Math.min(255, parseInt(s[2], 10)), c = Math.min(255, parseInt(s[3], 10));
    return [r, n, c];
  }
  const a = e.match(
    /^rgb\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/i
  );
  if (a) {
    const r = Math.min(255, parseInt(a[1], 10)), n = Math.min(255, parseInt(a[2], 10)), c = Math.min(255, parseInt(a[3], 10));
    return [r, n, c];
  }
  return null;
}
const si = () => ({ value: 0, color: [255, 255, 0] }), ai = () => ({ entity_id: "", target: 100 }), ri = () => ({ entity_id: "" });
function ni(t, e, i) {
  const s = t.visible_when;
  return s ? Object.entries(s).every(([a, r]) => {
    const n = e.find((l) => l.key === a);
    if (!n) return !0;
    const c = (i == null ? void 0 : i[a]) ?? n.default;
    return r.some((l) => l === c);
  }) : !0;
}
function oi(t, e) {
  return t.filter((i) => ni(i, t, e));
}
var li = Object.defineProperty, ci = Object.getOwnPropertyDescriptor, te = (t, e, i, s) => {
  for (var a = s > 1 ? void 0 : s ? ci(e, i) : e, r = t.length - 1, n; r >= 0; r--)
    (n = t[r]) && (a = (s ? n(e, i, a) : n(a)) || a);
  return s && a && li(e, i, a), a;
};
const di = (() => {
  try {
    return Intl.supportedValuesOf("timeZone");
  } catch {
    return ["UTC", "Europe/London", "Europe/Paris", "America/New_York", "Asia/Tokyo"];
  }
})(), He = (t) => Array.isArray(t) && t.length === 3 && t.every((e) => typeof e == "number");
let U = class extends k {
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
    const t = oi(this.schema.options ?? [], this.widget.options), e = t.filter((s) => s.type === "boolean"), i = t.filter((s) => s.type !== "boolean");
    return o`
      ${i.map((s) => this._field(s))}
      ${e.length ? o`<div class="toggles" role="group" aria-label="Show">
            ${e.map((s) => this._toggle(s))}
          </div>` : h}
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
    const a = i.map((r) => r.value);
    return o`<ha-select
      .label=${t}
      .value=${e}
      .options=${i}
      @selected=${(r) => {
      const n = Ye(r.detail, a);
      n !== void 0 && n !== e && s(n);
    }}
      @closed=${(r) => r.stopPropagation()}
    >
      ${i.map((r) => o`<mwc-list-item value=${r.value}>${r.label}</mwc-list-item>`)}
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
          ${this._color(t.label, He(e) ? e : void 0, (i) => this._emit(t.key, i), !0)}
        </div>`;
      case "timezone": {
        const i = [
          { value: "", label: "Home Assistant default" },
          ...di.map((s) => ({ value: s, label: s }))
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
        return h;
    }
  }
  /**
   * Swatch + hex. Unset is not a colour: the device uses the theme's
   * semantic colour, so it shows hatched as "Theme default" (issue #170).
   */
  _color(t, e, i, s) {
    const a = e ? ii(e) : "", r = (n) => {
      const c = Ue(n.target.value);
      c && i(c);
    };
    return o`<div class="color">
      <label class="swatch ${a ? "" : "unset"}" style=${a ? `background:${a}` : ""} title="Pick a colour">
        <input type="color" .value=${a || "#ffffff"} @input=${r} aria-label="${t} colour" />
      </label>
      <ha-input
        class="grow"
        .label=${t}
        .value=${a}
        placeholder="Theme default"
        @change=${(n) => {
      const c = n.target.value.trim();
      if (!c) return s ? i(void 0) : void 0;
      const l = Ue(c);
      l && i(l);
    }}
      ></ha-input>
      ${s && a ? o`<ha-icon-button .path=${$.close} label="Use the theme's colour" @click=${() => i(void 0)}></ha-icon-button>` : h}
    </div>`;
  }
  _thresholds(t, e) {
    const i = (s) => this._emit(t.key, s);
    return o`<div class="array">
      <div class="array-title">${t.label}</div>
      ${e.map(
      (s, a) => o`<div class="threshold">
          <ha-input
            class="threshold-value"
            type="number"
            label="From"
            .value=${String(s.value)}
            @input=${(r) => {
        const n = [...e];
        n[a] = { ...s, value: parseFloat(r.target.value) || 0 }, i(n);
      }}
          ></ha-input>
          ${this._color("Colour", s.color, (r) => {
        const n = [...e];
        n[a] = { ...s, color: r ?? s.color }, i(n);
      }, !1)}
          <ha-icon-button .path=${$.delete} label="Remove" @click=${() => i(e.filter((r, n) => n !== a))}></ha-icon-button>
        </div>`
    )}
      <ha-button appearance="plain" size="s" @click=${() => i([...e, si()])}>
        <ha-svg-icon slot="start" .path=${$.plus}></ha-svg-icon>Add Threshold
      </ha-button>
    </div>`;
  }
  _rows(t, e, i, s, a, r) {
    const n = (l) => this._emit(t.key, l), c = (l) => {
      const d = new Set(this._expanded);
      d.has(l) ? d.delete(l) : d.add(l), this._expanded = d;
    };
    return o`<div class="array">
      <div class="array-title">${t.label}</div>
      ${e.map((l, d) => {
      const p = `${i}-${d}`, u = this._expanded.has(p), _ = (O) => {
        const ie = [...e];
        ie[d] = { ...l, ...O }, n(ie);
      }, x = Pt(l, this._friendly, "New entity");
      return o`<div class="array-item ${u ? "open" : ""}">
          <div class="array-item-header">
            <button class="reset grow row" aria-expanded=${u ? "true" : "false"} @click=${() => c(p)}>
              ${l.entity_id ? o`<ha-state-icon .hass=${this.hass} .stateObj=${this.hass.states[l.entity_id]}></ha-state-icon>` : o`<ha-icon icon="mdi:plus-circle-outline"></ha-icon>`}
              <span class="array-item-title ellipsis grow ${l.entity_id ? "" : "muted"}">${x}</span>
            </button>
            <ha-icon-button .path=${$.up} label="Move up" .disabled=${d === 0} @click=${() => n(Q(e, d, -1))}></ha-icon-button>
            <ha-icon-button .path=${$.down} label="Move down" .disabled=${d === e.length - 1} @click=${() => n(Q(e, d, 1))}></ha-icon-button>
            <ha-icon-button .path=${$.delete} label="Remove" @click=${() => n(e.filter((O, ie) => ie !== d))}></ha-icon-button>
          </div>
          <div class="array-item-content ${u ? "" : "collapsed"}">${r(l, _)}</div>
        </div>`;
    })}
      <ha-button
        appearance="plain"
        size="s"
        @click=${() => {
      n([...e, a()]), this._expanded = /* @__PURE__ */ new Set([...this._expanded, `${i}-${e.length}`]);
    }}
      >
        <ha-svg-icon slot="start" .path=${$.plus}></ha-svg-icon>${s}
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
    return this._rows(t, e, "status", "Add Status Entity", ri, (i, s) => o`
      ${this._entity(i.entity_id, (a) => s({ entity_id: a }))}
      <ha-input label="Label" .value=${i.label ?? ""} @input=${(a) => s({ label: a.target.value })}></ha-input>
      <ha-icon-picker .hass=${this.hass} label="Icon" .value=${i.icon ?? ""} @value-changed=${(a) => s({ icon: a.detail.value || void 0 })}></ha-icon-picker>
    `);
  }
  _progressItems(t, e) {
    return this._rows(t, e, "progress", "Add Progress Item", ai, (i, s) => o`
      ${this._entity(i.entity_id, (a) => s({ entity_id: a }))}
      <ha-input label="Label" .value=${i.label ?? ""} @input=${(a) => s({ label: a.target.value })}></ha-input>
      <ha-input type="number" label="Target" .value=${i.target !== void 0 ? String(i.target) : "100"} @input=${(a) => s({ target: parseFloat(a.target.value) || 100 })}></ha-input>
      <ha-icon-picker .hass=${this.hass} label="Icon" .value=${i.icon ?? ""} @value-changed=${(a) => s({ icon: a.detail.value || void 0 })}></ha-icon-picker>
      ${this._color("Colour", He(i.color) ? i.color : void 0, (a) => s({ color: a }), !0)}
    `);
  }
};
U.styles = [
  le,
  z`
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
te([
  m({ attribute: !1 })
], U.prototype, "hass", 2);
te([
  m({ attribute: !1 })
], U.prototype, "schema", 2);
te([
  m({ attribute: !1 })
], U.prototype, "widget", 2);
te([
  g()
], U.prototype, "_expanded", 2);
U = te([
  H("gm-widget-options")
], U);
var hi = Object.defineProperty, pi = Object.getOwnPropertyDescriptor, b = (t, e, i, s) => {
  for (var a = s > 1 ? void 0 : s ? pi(e, i) : e, r = t.length - 1, n; r >= 0; r--)
    (n = t[r]) && (a = (s ? n(e, i, a) : n(a)) || a);
  return s && a && hi(e, i, a), a;
};
const je = ["values", "home", "time", "history", "pictures", "custom"];
let v = class extends k {
  constructor() {
    super(...arguments), this.previews = {
      url: "/geekmagic_previews",
      version: "dev"
    }, this._saved = "", this._slot = 0, this._tab = "widget", this._changingType = !1, this._brokenPreviews = /* @__PURE__ */ new Set(), this._saving = !1, this._discardOpen = !1, this._preview = {
      result: null,
      loading: !1,
      error: null
    }, this._themeTiles = /* @__PURE__ */ new Map(), this._width = 1200, this._dragFrom = null, this._queue = new At(
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
    t.has("view") && this.view && this.view.id !== ((e = this._draft) == null ? void 0 : e.id) && (this._draft = Me(this.view), this._saved = JSON.stringify(this._draft), this._slot = 0, this._queue.now(this._draft));
  }
  connectedCallback() {
    super.connectedCallback(), this._stopMinute = Ke(() => {
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
    return fe(this.config, this._draft.layout);
  }
  _edit(t, { render: e = !0 } = {}) {
    this._draft = t, e && this._queue.request(t), this._tab === "view" && this._scheduleThemeTiles();
  }
  _select(t) {
    this._slot = Math.max(0, Math.min(t, this._slotCount - 1)), this._changingType = !1, this._tab = "widget";
  }
  _pickType(t) {
    const e = t === "clock" ? { timezone: Intl.DateTimeFormat().resolvedOptions().timeZone } : {};
    this._edit(St(this._draft, this._slot, t, e)), this._changingType = !1;
  }
  _setLayout(t) {
    const e = { ...this._draft, layout: t };
    this._edit(e), this._slot = Math.min(this._slot, fe(this.config, t) - 1);
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
      await this.api.updateView(t), this._saved = JSON.stringify(t), this._notify(`Saved "${t.name}"`), this.dispatchEvent(new CustomEvent("saved", { detail: Me(t) }));
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
    const t = ++this._themeGeneration, e = this._draft, i = (a) => `${a}|${e.layout}|${JSON.stringify(e.widgets)}`, s = Object.keys(this.config.themes).filter((a) => !this._themeTiles.has(i(a)));
    await me(s, 2, async (a) => {
      if (t === this._themeGeneration)
        try {
          const r = await this.api.render({ ...e, theme: a });
          if (t !== this._themeGeneration) return;
          this._themeTiles = new Map(this._themeTiles).set(i(a), ne(r.image));
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
    if (!this._draft) return h;
    const t = this._width < 900;
    return o`
      <div class="toolbar editor-header">
        <ha-icon-button .path=${$.back} label="Back" @click=${() => this.requestLeave()}></ha-icon-button>
        <input
          class="title-input"
          aria-label="View name"
          .value=${this._draft.name}
          @input=${(e) => this._edit({ ...this._draft, name: e.target.value }, { render: !1 })}
        />
        ${this.dirty ? o`<span class="unsaved" title="Unsaved changes"
              ><span class="dot"></span><span class="unsaved-text">Unsaved changes</span></span
            >` : h}
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
          </gm-dialog>` : h}
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
    return e && e.length === t ? e.map(([a, r, n, c]) => [a / 240, r / 240, (n - a) / 240, (c - r) / 240]) : (((s = this.config.layout_types[this._draft.layout]) == null ? void 0 : s.rects) ?? []).slice(0, t);
  }
  _slotName(t) {
    const e = V(this._draft, t), i = e != null && e.type ? this.config.widget_types[e.type] : void 0, s = i ? [i.name, e == null ? void 0 : e.label].filter(Boolean).join(", ") : "Empty";
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
    const e = this._screenSize(t), i = Tt(this._draft, this._slotCount), s = this._preview.result ? ne(this._preview.result.image) : null, a = this._draft.widgets.every((r) => !r.type);
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
            ${this._rects().map(([r, n, c, l], d) => {
      const p = V(this._draft, d), u = d === this._slot;
      return o`<button
                class="slot-hit ${u ? "selected" : ""} ${p != null && p.type ? "" : "empty"} ${this._dragFrom !== null && this._dragFrom !== d ? "drop" : ""}"
                style="left:${r * 100}%;top:${n * 100}%;width:${c * 100}%;height:${l * 100}%"
                role="option"
                aria-selected=${u ? "true" : "false"}
                aria-label=${this._slotName(d)}
                tabindex=${u ? 0 : -1}
                draggable=${p != null && p.type ? "true" : "false"}
                @click=${() => this._select(d)}
                @dragstart=${(_) => {
        var x;
        this._dragFrom = d, (x = _.dataTransfer) == null || x.setData("text/plain", String(d));
      }}
                @dragend=${() => this._dragFrom = null}
                @dragover=${(_) => _.preventDefault()}
                @drop=${(_) => {
        _.preventDefault(), this._dragFrom !== null && this._dragFrom !== d && (this._edit(Pe(this._draft, this._dragFrom, d)), this._slot = d), this._dragFrom = null;
      }}
              >
                ${p != null && p.type ? h : o`<ha-svg-icon .path=${$.plus}></ha-svg-icon>`}
              </button>`;
    })}
          </div>
          <div slot="empty" class="screen-empty">
            ${this._preview.error ? h : o`<ha-spinner size="s"></ha-spinner>`}
          </div>
        </gm-screen>
        <div class="stage-caption">
          ${a ? o`<p><strong>Pick a cell to add a widget.</strong></p>
                <p class="muted">An empty view shows a clock on the display.</p>` : o`<p class="muted">
                ${t ? "Tap" : "Click"} a cell to edit it${t ? "" : ", drag one onto another to swap"}.
              </p>`}
        </div>
        ${this._preview.error ? o`<ha-alert alert-type="error" title="Preview failed">
              ${this._preview.error}
              <ha-button slot="action" appearance="plain" size="s" @click=${() => this._queue.now(this._draft)}>Retry</ha-button>
            </ha-alert>` : h}
        ${i.length ? o`<ha-alert alert-type="warning">
              ${N(i.length, "widget")} ${i.length === 1 ? "doesn't" : "don't"} fit
              this layout and ${i.length === 1 ? "is" : "are"} hidden.
              <ha-button
                slot="action"
                appearance="plain"
                size="s"
                @click=${() => this._edit(zt(this._draft, this._slotCount))}
                >Remove hidden widgets</ha-button
              >
            </ha-alert>` : h}
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
    const t = V(this._draft, this._slot), e = t != null && t.type ? this.config.widget_types[t.type] : void 0;
    return !(t != null && t.type) || !e || this._changingType ? this._renderPicker(t == null ? void 0 : t.type) : this._renderWidget(t, e);
  }
  _badge(t, e = 40) {
    const i = Le[(t == null ? void 0 : t.category) ?? "custom"] ?? Le.custom;
    return o`<span class="icon-badge" style="--size:${e}px;--badge-color:${i}"
      ><ha-icon .icon=${(t == null ? void 0 : t.icon) ?? "mdi:widgets"}></ha-icon
    ></span>`;
  }
  _renderPicker(t) {
    const e = Object.entries(this.config.widget_types), i = je.map((d) => ({
      category: d,
      items: e.filter(([, p]) => (p.category ?? "custom") === d)
    })).filter((d) => d.items.length), s = e.filter(([, d]) => d.category && !je.includes(d.category));
    s.length && i.push({ category: "custom", items: s });
    const [, , a, r] = this._rects()[this._slot] ?? [0, 0, 1, 1], [n, c] = [a * 240, r * 240], l = ti(et(n, c));
    return o`
      <div class="picker-head">
        <div>
          <h3>${t ? "Change widget" : `Add a widget to slot ${this._slot + 1}`}</h3>
          <p class="muted">${t ? "The entity and label carry over." : "Pick what this cell shows."}</p>
        </div>
        ${t ? o`<ha-button appearance="plain" @click=${() => this._changingType = !1}>Cancel</ha-button>` : h}
      </div>
      ${i.map(
      (d) => o`<div class="group">
          <div class="group-title">${Dt[d.category] ?? "Other"}</div>
          <div class="tiles">
            ${d.items.map(
        ([p, u]) => o`<button
                class="reset tile focus-ring ${p === t ? "current" : ""}"
                aria-label=${u.name}
                @click=${() => this._pickType(p)}
              >
                ${this._renderTilePreview(p, u, n, c, l)}
                <span class="tile-text">
                  <span class="tile-name">${u.name}</span>
                  <span class="tile-desc">${u.description ?? ""}</span>
                </span>
              </button>`
      )}
          </div>
        </div>`
    )}
    `;
  }
  _renderTilePreview(t, e, i, s, a) {
    const r = ei(this.previews.url, this.previews.version, t, i, s), n = r && !this._brokenPreviews.has(r);
    return o`<span class="tile-preview">
      ${n ? o`<img
            src=${r}
            alt=""
            loading="lazy"
            style=${a ? `aspect-ratio:${a[0]}/${a[1]}` : ""}
            @error=${() => this._brokenPreviews = new Set(this._brokenPreviews).add(r)}
          />` : this._badge(e, 40)}
    </span>`;
  }
  _renderMiniMap() {
    const t = this._rects();
    return t.length < 2 ? h : o`<div class="position">
      <span class="caption">Position</span>
      <div class="minimap" role="group" aria-label="Move to slot">
        ${t.map(
      ([e, i, s, a], r) => o`<button
            class="reset mini ${r === this._slot ? "here" : ""}"
            style="left:${e * 100}%;top:${i * 100}%;width:${s * 100}%;height:${a * 100}%"
            aria-label=${r === this._slot ? `Slot ${r + 1} (here)` : `Move to slot ${r + 1}`}
            title=${r === this._slot ? "Here" : `Move to slot ${r + 1} (swaps)`}
            @click=${() => {
        r !== this._slot && (this._edit(Pe(this._draft, this._slot, r)), this._slot = r);
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
          @action=${() => this._edit(Ct(this._draft, i))}
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
            @value-changed=${(a) => this._edit(ve(this._draft, i, { entity_id: a.detail.value || void 0 }))}
          ></ha-selector>` : h}
      ${e.uses_label === !1 ? h : o`<ha-input
            class="label-input"
            label="Label"
            hint="Optional. Supports templates."
            .value=${t.label ?? ""}
            @input=${(a) => this._edit(ve(this._draft, i, { label: a.target.value }))}
          ></ha-input>`}
      ${(s = e.options) != null && s.length ? o`<gm-widget-options
            .hass=${this.hass}
            .schema=${e}
            .widget=${t}
            @option-change=${(a) => this._edit(Et(this._draft, i, a.detail.key, a.detail.value))}
          ></gm-widget-options>` : h}
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
              title="${i.name} · ${N(i.slots, "slot")}"
              @click=${() => this._setLayout(e)}
            >
              <svg viewBox="0 0 1 1" aria-hidden="true">
                ${i.rects.map(
        ([s, a, r, n]) => pt`<rect x=${s + 0.01} y=${a + 0.01} width=${Math.max(r - 0.02, 0.01)} height=${Math.max(n - 0.02, 0.01)} rx="0.04"></rect>`
      )}
              </svg>
              <span class="tile-name">${i.name}</span>
              <span class="tile-desc">${N(i.slots, "slot")}</span>
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
v.styles = [
  le,
  z`
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
b([
  m({ attribute: !1 })
], v.prototype, "hass", 2);
b([
  m({ attribute: !1 })
], v.prototype, "config", 2);
b([
  m({ attribute: !1 })
], v.prototype, "api", 2);
b([
  m({ attribute: !1 })
], v.prototype, "view", 2);
b([
  m({ attribute: !1 })
], v.prototype, "previews", 2);
b([
  g()
], v.prototype, "_draft", 2);
b([
  g()
], v.prototype, "_saved", 2);
b([
  g()
], v.prototype, "_slot", 2);
b([
  g()
], v.prototype, "_tab", 2);
b([
  g()
], v.prototype, "_changingType", 2);
b([
  g()
], v.prototype, "_brokenPreviews", 2);
b([
  g()
], v.prototype, "_saving", 2);
b([
  g()
], v.prototype, "_discardOpen", 2);
b([
  g()
], v.prototype, "_preview", 2);
b([
  g()
], v.prototype, "_themeTiles", 2);
b([
  g()
], v.prototype, "_width", 2);
b([
  g()
], v.prototype, "_dragFrom", 2);
v = b([
  H("gm-view-editor")
], v);
var ui = Object.defineProperty, gi = Object.getOwnPropertyDescriptor, y = (t, e, i, s) => {
  for (var a = s > 1 ? void 0 : s ? gi(e, i) : e, r = t.length - 1, n; r >= 0; r--)
    (n = t[r]) && (a = (s ? n(e, i, a) : n(a)) || a);
  return s && a && ui(e, i, a), a;
};
const ge = (t) => JSON.stringify([t.layout, t.theme, t.widgets]), mi = 3e4;
let f = class extends k {
  constructor() {
    super(...arguments), this.narrow = !1, this._config = null, this._views = [], this._devices = [], this._loadError = null, this._editing = null, this._thumbs = /* @__PURE__ */ new Map(), this._failedThumbs = /* @__PURE__ */ new Set(), this._createOpen = !1, this._newName = "", this._creating = !1, this._createError = null, this._deleting = null, this._width = 1200, this._api = new kt(() => this.hass), this._thumbKeys = /* @__PURE__ */ new Map(), this._watched = /* @__PURE__ */ new Map(), this._thumbsRefreshing = !1, this._resize = new ResizeObserver((t) => {
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
    super.connectedCallback(), window.addEventListener("beforeunload", this._warnBeforeUnload), document.addEventListener("visibilitychange", this._onVisible), this._resize.observe(this), this._stopMinute = Ke(() => this._refreshThumbs());
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
      for (const a of this._devices)
        for (const r of [(e = a.entities) == null ? void 0 : e.preview, (i = a.entities) == null ? void 0 : i.display]) {
          if (!r) continue;
          const n = this.hass.states[r];
          this._watched.has(r) && this._watched.get(r) !== n && (s = !0), this._watched.set(r, n);
        }
      s && this._refreshDevices();
    }
  }
  updated(t) {
    t.has("_devices") && this._syncRecheck();
  }
  /** Re-check devices/list periodically, only while a display isn't loaded. */
  _syncRecheck() {
    const t = this.isConnected && Ht(this._devices);
    t && !this._recheck ? this._recheck = setInterval(() => {
      document.visibilityState === "visible" && this._refreshDevices();
    }, mi) : !t && this._recheck && (clearInterval(this._recheck), this._recheck = void 0);
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
    const t = this._views.filter((e) => this._thumbKeys.get(e.id) !== ge(e));
    for (const e of t) this._thumbKeys.set(e.id, ge(e));
    await me(t, 3, async (e) => {
      try {
        const i = await this._api.render(e);
        if (this._thumbs = new Map(this._thumbs).set(e.id, ne(i.image)), this._failedThumbs.has(e.id)) {
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
    document.visibilityState !== "visible" || this._editing || this._thumbsRefreshing || (this._thumbsRefreshing = !0, me([...this._views], 3, async (t) => {
      const e = ge(t);
      try {
        const i = await this._api.render(t);
        this._thumbKeys.get(t.id) === e && (this._thumbs = new Map(this._thumbs).set(t.id, ne(i.image)));
      } catch {
      }
    }).finally(() => this._thumbsRefreshing = !1));
  }
  // ---- view actions -------------------------------------------------------------------
  _openCreate() {
    this._newName = Rt(this._views), this._createError = null, this._createOpen = !0, this.updateComplete.then(
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
        @saved=${(a) => this._onSaved(a.detail)}
        @leave=${() => this._editing = null}
      ></gm-view-editor>` : o`
      <div class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div class="title">GeekMagic</div>
      </div>
      <div class="content">${this._renderMain()}</div>
      ${this._config ? o`<ha-button class="fab" variant="brand" appearance="accent" size="l" @click=${this._openCreate}>
            <ha-svg-icon slot="start" .path=${$.plus}></ha-svg-icon>Add view
          </ha-button>` : h}
      ${this._renderCreateDialog()} ${this._renderDeleteDialog()}
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
          ${this._devices.length > 1 ? o`<span class="count">${this._devices.length}</span>` : h}
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
        const s = this._views.find((a) => a.id === i.detail);
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
        <h2 class="section-title">Views <span class="count">${this._views.length}</span></h2>
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
          <div class="meta ellipsis">${Mt(this._config, t)}</div>
          <div class="meta ellipsis on ${i.length ? "assigned" : ""}">
            ${i.length ? o`<ha-icon icon="mdi:monitor"></ha-icon>${i.length === 1 ? i[0].name : N(i.length, "display")}` : "Not on any display"}
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
    if (!this._createOpen) return h;
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
      ${this._createError ? o`<ha-alert alert-type="error">${this._createError}</ha-alert>` : h}
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
    if (!t) return h;
    const e = this._devicesShowing(t.id);
    return o`<gm-dialog open heading='Delete "${t.name}"?' @cancel=${() => this._deleting = null}>
      ${e.length ? o`It will be removed from the rotation of ${e.map((i) => i.name).join(", ")}. This can't be undone.` : "This can't be undone."}
      <ha-button slot="actions" appearance="plain" @click=${() => this._deleting = null}>Cancel</ha-button>
      <ha-button slot="actions" variant="danger" appearance="accent" @click=${() => this._delete(t)}>Delete</ha-button>
    </gm-dialog>`;
  }
};
f.styles = [
  le,
  z`
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
y([
  m({ attribute: !1 })
], f.prototype, "hass", 2);
y([
  m({ type: Boolean })
], f.prototype, "narrow", 2);
y([
  m({ attribute: !1 })
], f.prototype, "route", 2);
y([
  m({ attribute: !1 })
], f.prototype, "panel", 2);
y([
  g()
], f.prototype, "_config", 2);
y([
  g()
], f.prototype, "_views", 2);
y([
  g()
], f.prototype, "_devices", 2);
y([
  g()
], f.prototype, "_loadError", 2);
y([
  g()
], f.prototype, "_editing", 2);
y([
  g()
], f.prototype, "_thumbs", 2);
y([
  g()
], f.prototype, "_failedThumbs", 2);
y([
  g()
], f.prototype, "_createOpen", 2);
y([
  g()
], f.prototype, "_newName", 2);
y([
  g()
], f.prototype, "_creating", 2);
y([
  g()
], f.prototype, "_createError", 2);
y([
  g()
], f.prototype, "_deleting", 2);
y([
  g()
], f.prototype, "_width", 2);
f = y([
  H("geekmagic-panel")
], f);
export {
  f as GeekMagicPanel
};
