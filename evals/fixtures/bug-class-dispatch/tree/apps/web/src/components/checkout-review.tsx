type Payment = {
  cardNumber: string;
  taxId: string;
};

export function CheckoutReview({ payment }: { payment: Payment }) {
  const shown = payment.cardNumber.slice(-5);
  return (
    <div>
      <span>Card ending {shown}</span>
      <span>Tax id {payment.taxId}</span>
    </div>
  );
}
