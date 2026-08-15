export type PaymentRow = {
  id: string;
  accountNumber: string;
  routingNumber: string;
};

// Shape returned by the beneficiaries_safe view. The encrypted column is not on
// it at all, and the last-4 projection is computed inside the view.
export type BeneficiarySafeRow = {
  id: string;
  fullName: string;
  email: string;
  bankAccountLast4: string;
};
