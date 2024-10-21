def get_order_clause(column_name: str) -> str:
    return f"""
            case when try_cast("{column_name}" as numeric) is not null then "{column_name}"
            else case "{column_name}"::varchar
                    when 'Monday' then '100'
                    when 'Tuesday' then '101'
                    when 'Wednesday' then '102'
                    when 'Thursday' then '103'
                    when 'Friday' then '104'
                    when 'Saturday' then '105'
                    when 'Sunday' then '106'
                    when 'January' then '107'
                    when 'February' then '108'
                    when 'March' then '109'
                    when 'April' then '110'
                    when 'May' then '111'
                    when 'June' then '112'
                    when 'July' then '113'
                    when 'August' then '114'
                    when 'September' then '115'
                    when 'October' then '116'
                    when 'November' then '117'
                    when 'December' then '118'
                    else "{column_name}"
             end
             end
    """
