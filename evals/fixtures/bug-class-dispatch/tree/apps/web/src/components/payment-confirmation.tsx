type ConfirmedBeneficiary = {
  fullName: string;
  bankAccountLast4: string;
};

export function PaymentConfirmation({
  beneficiary,
}: {
  beneficiary: ConfirmedBeneficiary;
}) {
  // bankAccountLast4 is projected by the beneficiaries_safe view and passes
  // through serializeBeneficiary unchanged, so nothing longer arrives here.
  return (
    <div>
      <span>{beneficiary.fullName}</span>
      <span>Account ending {beneficiary.bankAccountLast4}</span>
    </div>
  );
}
