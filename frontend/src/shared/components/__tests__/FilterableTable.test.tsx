import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import { FilterableTable, type Column } from "@/shared/components/FilterableTable";

interface TestRow extends Record<string, unknown> {
  id: string;
  name: string;
  value: number;
}

const columns: Column<TestRow>[] = [
  { key: "name", label: "Name", sortable: true },
  { key: "value", label: "Value", sortable: true },
];

const sampleData: TestRow[] = [
  { id: "1", name: "Alpha", value: 10 },
  { id: "2", name: "Beta", value: 20 },
  { id: "3", name: "Gamma", value: 30 },
];

afterEach(cleanup);

describe("FilterableTable", () => {
  it("renders with data", () => {
    render(
      <FilterableTable columns={columns} data={sampleData} total={3} />,
    );
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
    expect(screen.getByText("Gamma")).toBeInTheDocument();
  });

  it("shows search input when onSearch is provided", () => {
    render(
      <FilterableTable
        columns={columns}
        data={sampleData}
        total={3}
        onSearch={vi.fn()}
      />,
    );
    expect(screen.getByPlaceholderText("Buscar...")).toBeInTheDocument();
  });

  it("calls onSearch when user types", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    render(
      <FilterableTable
        columns={columns}
        data={sampleData}
        total={3}
        onSearch={onSearch}
      />,
    );

    await user.type(screen.getByPlaceholderText("Buscar..."), "Alpha");

    await waitFor(() => {
      expect(onSearch).toHaveBeenCalledWith("Alpha");
    });
  });

  it("shows pagination when total exceeds pageSize", () => {
    const manyItems = Array.from({ length: 30 }, (_, i) => ({
      id: String(i + 1),
      name: `Item ${i + 1}`,
      value: i,
    }));

    render(
      <FilterableTable
        columns={columns}
        data={manyItems}
        total={30}
        pageSize={25}
      />,
    );

    expect(screen.getByText("1–25 de 30")).toBeInTheDocument();
    expect(screen.getByText("Siguiente")).toBeInTheDocument();
    expect(screen.getByText("Anterior")).toBeInTheDocument();
  });

  it("hides pagination when total is within pageSize", () => {
    render(
      <FilterableTable columns={columns} data={sampleData} total={3} />,
    );

    expect(screen.queryByText("Siguiente")).not.toBeInTheDocument();
    expect(screen.queryByText("Anterior")).not.toBeInTheDocument();
  });

  it("shows empty state when data is empty and not loading", () => {
    render(
      <FilterableTable columns={columns} data={[]} total={0} />,
    );

    expect(
      screen.getByText("No se encontraron resultados"),
    ).toBeInTheDocument();
  });

  it("shows loading state instead of data", () => {
    render(
      <FilterableTable
        columns={columns}
        data={[]}
        total={0}
        isLoading={true}
      />,
    );

    expect(screen.queryByText("Alpha")).not.toBeInTheDocument();
  });

  it("shows error state", () => {
    render(
      <FilterableTable
        columns={columns}
        data={[]}
        total={0}
        error="Error de conexión"
      />,
    );

    expect(screen.getByText("Error de conexión")).toBeInTheDocument();
  });

  it("renders custom column render function", () => {
    const customColumns: Column<TestRow>[] = [
      {
        key: "name",
        label: "Name",
        render: (row) => <strong>{row.name}</strong>,
      },
    ];

    render(
      <FilterableTable columns={customColumns} data={sampleData} total={3} />,
    );

    const bold = screen.getByText("Alpha");
    expect(bold.tagName).toBe("STRONG");
  });
});
