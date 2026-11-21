"""Simulações unitárias de custos, explicitamente informados pelo operador.
Nenhuma alíquota legal é inferida; os resultados não são apuração tributária.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

D = lambda value: Decimal(str(value))
CENT = Decimal('0.01')


def rounded(value):
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP)) if value is not None else None


class CostInputs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    # Preço da captura é indicativo; override pode representar cotação negociada.
    purchase_override_brl: Optional[float] = Field(default=None, ge=0, le=1e9, allow_inf_nan=False)
    shipping_brl: Optional[float] = Field(default=None, ge=0, le=1e9, allow_inf_nan=False)
    import_tax_pct: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    import_fixed_brl: float = Field(default=0, ge=0, le=1e9, allow_inf_nan=False)
    marketplace_pct: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    payment_pct: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    sales_tax_pct: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    return_reserve_pct: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    marketplace_fixed_brl: float = Field(default=0, ge=0, le=1e9, allow_inf_nan=False)
    payment_fixed_brl: float = Field(default=0, ge=0, le=1e9, allow_inf_nan=False)
    packaging_brl: float = Field(default=0, ge=0, le=1e9, allow_inf_nan=False)
    advertising_brl: float = Field(default=0, ge=0, le=1e9, allow_inf_nan=False)
    other_brl: float = Field(default=0, ge=0, le=1e9, allow_inf_nan=False)
    sale_price_brl: Optional[float] = Field(default=None, gt=0, le=1e9, allow_inf_nan=False)
    target_margin_pct: Optional[float] = Field(default=None, ge=0, lt=100, allow_inf_nan=False)
    notes: Optional[str] = Field(default=None, max_length=500)


def analyze_costs(inputs: CostInputs, observed_price_brl=None, fx_is_fallback=False):
    purchase = inputs.purchase_override_brl if inputs.purchase_override_brl is not None else observed_price_brl
    blockers = []
    if purchase is None: blockers.append('Preço de compra indisponível; informe uma cotação manual em BRL.')
    if inputs.shipping_brl is None: blockers.append('Frete por unidade não confirmado (informe 0 somente se comprovadamente grátis).')
    if inputs.sale_price_brl is None: blockers.append('Preço de venda não informado; lucro e margem indisponíveis.')
    if inputs.purchase_override_brl is None and fx_is_fallback:
        blockers.append('Câmbio de contingência: confirme a cotação antes de decidir.')
    # Componentes preenchidos são premissas, nunca tributos verificados.
    configured = [
        'import_tax_pct','import_fixed_brl','marketplace_pct','payment_pct',
        'sales_tax_pct','return_reserve_pct','marketplace_fixed_brl',
        'payment_fixed_brl','packaging_brl','advertising_brl','other_brl',
    ]
    zero_assumptions = [k for k in configured if getattr(inputs, k) == 0]
    result = {'status': 'incompleto' if blockers else 'simulado', 'warnings': blockers,
              'zero_assumptions': zero_assumptions, 'currency': 'BRL',
              'purchase_brl': rounded(D(purchase)) if purchase is not None else None,
              'shipping_brl': inputs.shipping_brl, 'estimated': True,
              'source_price': 'manual' if inputs.purchase_override_brl is not None else 'captura_convertida'}
    if purchase is None or inputs.shipping_brl is None:
        return {**result, 'import_tax_brl': None, 'fixed_cost_brl': None,
                'variable_rate_pct': None, 'break_even_brl': None, 'target_sale_price_brl': None,
                'variable_fees_brl': None, 'total_cost_brl': None, 'profit_brl': None,
                'margin_pct': None, 'roi_pct': None, 'sensitivity': None}
    base = D(purchase) + D(inputs.shipping_brl)
    import_tax = base * D(inputs.import_tax_pct) / 100
    fixed = (base + import_tax + sum((D(getattr(inputs, k)) for k in [
        'import_fixed_brl','marketplace_fixed_brl','payment_fixed_brl',
        'packaging_brl','advertising_brl','other_brl']), D(0)))
    variable_pct = sum((D(getattr(inputs, k)) for k in [
        'marketplace_pct','payment_pct','sales_tax_pct','return_reserve_pct']), D(0))
    variable = variable_pct / 100
    break_even = fixed / (1-variable) if variable < 1 else None
    target = D(inputs.target_margin_pct) / 100 if inputs.target_margin_pct is not None else None
    target_sale = fixed / (1-variable-target) if target is not None and variable + target < 1 else None
    sale = D(inputs.sale_price_brl) if inputs.sale_price_brl is not None else None
    variable_fees = sale * variable if sale is not None else None
    total = fixed + variable_fees if sale is not None else None
    profit = sale - total if sale is not None else None
    sensitivity = None
    if sale is not None:
        scenarios = {
            'sale_minus_10_pct': (sale * D('0.90'), fixed),
            'purchase_plus_10_pct': (sale, fixed + D(purchase) * D('0.10') * (1 + D(inputs.import_tax_pct) / 100)),
            'combined_stress': (sale * D('0.90'), fixed + D(purchase) * D('0.10') * (1 + D(inputs.import_tax_pct) / 100)),
        }
        sensitivity = {key: {'profit_brl': rounded(sv * (1-variable) - fc),
                             'margin_pct': rounded((sv * (1-variable) - fc) / sv * 100)}
                       for key, (sv, fc) in scenarios.items()}
    if variable >= 1: result['warnings'].append('Taxas variáveis ≥ 100%: não existe preço de equilíbrio positivo.')
    if target is not None and variable + target >= 1:
        result['warnings'].append('Meta de margem inviável com as taxas variáveis definidas.')
    return {**result, 'import_tax_brl': rounded(import_tax),
            'fixed_cost_brl': rounded(fixed), 'variable_rate_pct': rounded(variable_pct),
            'break_even_brl': rounded(break_even), 'target_sale_price_brl': rounded(target_sale),
            'variable_fees_brl': rounded(variable_fees), 'total_cost_brl': rounded(total),
            'profit_brl': rounded(profit), 'margin_pct': rounded(profit / sale * 100) if profit is not None else None,
            'roi_pct': rounded(profit / total * 100) if profit is not None and total > 0 else None,
            'sensitivity': sensitivity}
