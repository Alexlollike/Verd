"""
GompertzMakeham — konkret dødelighedsmodel.

Implementerer Gompertz-Makeham intensiteten:

    µ(x) = alpha + beta · exp(sigma · x)

Parametre:
    alpha  : Makeham-led — aldersuafhængig baggrundsintensitet (ulykker, sygdom)
    beta   : Gompertz-led præfaktor
    sigma  : Gompertz-vækstrate (styrken af aldringsleddet)

Typiske danske værdier (mand, G82-lignende):
    alpha ≈ 0.0005,  beta ≈ 0.00004,  sigma ≈ 0.09
"""

import math
from dataclasses import dataclass

from verd.biometric_model import BiometricModel


@dataclass
class GompertzMakeham(BiometricModel):
    """
    Gompertz-Makeham dødelighedsmodel.

    Dødelighedsintensiteten er:

        µ(x) = alpha + beta · exp(sigma · x)

    hvor x er forsikringstagers alder i år.

    Attributes
    ----------
    alpha:
        Makeham-konstantled (aldersuafhængig intensitet). alpha ≥ 0.
    beta:
        Gompertz-præfaktor. beta ≥ 0.
    sigma:
        Gompertz-vækstrate (aldringens styrke). sigma > 0.
    """

    alpha: float
    beta: float
    sigma: float

    def mortality_intensity(self, alder: float) -> float:
        """
        Beregn dødelighedsintensiteten µ(x) ved alder x.

            µ(x) = alpha + beta · exp(sigma · x)

        Parameters
        ----------
        alder:
            Forsikringstagers alder i år.

        Returns
        -------
        float
            µ(x) ≥ 0, målt i år⁻¹.
        """
        return self.alpha + self.beta * math.exp(self.sigma * alder)
