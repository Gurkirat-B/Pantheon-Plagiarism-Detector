import { Loader2 } from "lucide-react";
import { Button, ButtonProps } from "@/components/ui/button";
import { forwardRef } from "react";

type LoadingButtonProps = ButtonProps & {
  loading?: boolean;
};

const LoadingButton = forwardRef<HTMLButtonElement, LoadingButtonProps>(
  ({ loading = false, children, ...props }, ref) => {
    return (
      <Button disabled={loading} ref={ref} {...props}>
        <>
          {loading && <Loader2 className="animate-spin" />}
          {children}
        </>
      </Button>
    );
  },
);

LoadingButton.displayName = "LoadingButton";

export { LoadingButton };
